import time
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import xgboost as xgb
import psutil
import os
import gc
from sklearn.preprocessing import MinMaxScaler

# --- CONFIGURATION ---
LSTM_UNITS = 64  # "Light" Architecture
LOOKBACK = 60    # 60 bars of history
TEST_ITERATIONS = 100 

print("="*60)
print("🧪 HYBRID MODEL SANDBOX: PYTORCH CPU + QUANTIZATION")
print("="*60)
print(f"CPU Cores Detected: {os.cpu_count()}")
print(f"Target Architecture: LSTM (Dynamic Quantization) -> XGBoost")
print("-" * 60)

# --- 1. GENERATE DUMMY DATA ---
print("[1/5] Generating Synthetic NQ Data...")
data_size = 5000
# Features: Close, High, Low, Vol, RSI, MACD
df = pd.DataFrame(np.random.random((data_size, 6)), columns=['Close', 'High', 'Low', 'Vol', 'RSI', 'MACD'])
targets = np.random.randint(0, 2, data_size)

scaler = MinMaxScaler()
scaled_data = scaler.fit_transform(df)

X_seq, y_seq = [], []
for i in range(LOOKBACK, len(scaled_data)):
    X_seq.append(scaled_data[i-LOOKBACK:i])
    y_seq.append(targets[i])
X_seq = torch.FloatTensor(np.array(X_seq)) # Convert to PyTorch Tensor
y_seq = np.array(y_seq)

print(f"      Data Shape: {X_seq.shape} (Ready for Training)")

# --- 2. BUILD LIGHTWEIGHT LSTM (PyTorch) ---
print("[2/5] Training 'Light' LSTM (Sequence Reader)...")

class LightLSTM(nn.Module):
    def __init__(self, input_size=6, hidden_layer_size=64, output_size=1):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_layer_size, batch_first=True)
        self.linear = nn.Linear(hidden_layer_size, output_size)
        self.sigmoid = nn.Sigmoid()

    def forward(self, input_seq):
        lstm_out, _ = self.lstm(input_seq)
        # We only want the last time step output
        last_step = lstm_out[:, -1, :] 
        predictions = self.linear(last_step)
        return self.sigmoid(predictions)

model = LightLSTM(input_size=6, hidden_layer_size=LSTM_UNITS)
criterion = nn.BCELoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

# Fast Training Loop (1 Epoch for Sandbox Speed)
model.train()
targets_tensor = torch.FloatTensor(y_seq).view(-1, 1)
optimizer.zero_grad()
y_pred = model(X_seq)
loss = criterion(y_pred, targets_tensor)
loss.backward()
optimizer.step()
print("      LSTM Trained.")

# --- 3. QUANTIZATION (The Speed Hack) ---
print("[3/5] Applying 8-bit Dynamic Quantization...")
# PyTorch allows dynamic quantization of Linear and LSTM layers specifically for CPUs
quantized_model = torch.quantization.quantize_dynamic(
    model, {nn.LSTM, nn.Linear}, dtype=torch.qint8
)
print("      Quantization Complete (Int8 weights applied).")

# --- 4. TRAIN XGBOOST (Sequential Integration) ---
print("[4/5] Training XGBoost with Sequential Integration...")

# A. Get LSTM Predictions (The "Super Feature")
# We use no_grad to save memory during inference
with torch.no_grad():
    lstm_features = quantized_model(X_seq).numpy().flatten()

# B. Prepare XGBoost Inputs
# Input = [Original Indicators] + [LSTM_Trend_Feature]
X_xgb = df.iloc[LOOKBACK:].copy()
X_xgb['LSTM_Feature'] = lstm_features 

# Train XGBoost
xgb_model = xgb.XGBClassifier(n_estimators=50, max_depth=3, n_jobs=-1)
xgb_model.fit(X_xgb, y_seq)
print("      XGBoost Trained & Integrated.")

# --- 5. LATENCY STRESS TEST ---
print("-" * 60)
print(f"[5/5] RUNNING LATENCY STRESS TEST ({TEST_ITERATIONS} iterations)...")

latencies = []
start_mem = psutil.Process().memory_info().rss / (1024 * 1024)

# Prepare a single live sample for the loop
sample_input = X_seq[0:1] # Shape [1, 60, 6]

for i in range(TEST_ITERATIONS):
    start_time = time.time()
    
    # STEP A: Run Quantized LSTM
    with torch.no_grad():
        lstm_out = quantized_model(sample_input).item()
    
    # STEP B: Run XGBoost
    # Create single row with features + LSTM output
    # (Simulating reading current market data)
    current_features = pd.DataFrame(np.random.random((1, 6)), columns=['Close', 'High', 'Low', 'Vol', 'RSI', 'MACD'])
    current_features['LSTM_Feature'] = lstm_out
    
    final_decision = xgb_model.predict_proba(current_features)[0][1]
    
    end_time = time.time()
    latencies.append((end_time - start_time) * 1000) # ms

    if i % 10 == 0: gc.collect()

end_mem = psutil.Process().memory_info().rss / (1024 * 1024)

# --- RESULTS ---
avg_lat = np.mean(latencies)
max_lat = np.max(latencies)
p99_lat = np.percentile(latencies, 99)

print("="*60)
print("🚀 SANDBOX RESULTS (PYTORCH CPU)")
print("="*60)
print(f"MEMORY USAGE:")
print(f"  Start: {start_mem:.2f} MB")
print(f"  End:   {end_mem:.2f} MB")
print(f"  Delta: {end_mem - start_mem:.2f} MB")
print("-" * 30)
print(f"LATENCY (Speed Limit: 100ms):")
print(f"  Average: {avg_lat:.2f} ms")
print(f"  Max:     {max_lat:.2f} ms")
print(f"  99th %:  {p99_lat:.2f} ms")
print("-" * 30)

if avg_lat < 100:
    print("✅ STATUS: PASSED. Architecture is FAST enough for Sniper.")
else:
    print("⚠️ STATUS: WARNING. Latency is too high.")
print("="*60)