import os
import sys
import logging
import json
import glob
import numpy as np
import pandas as pd
import io
import datetime
import pickle

print("🔵 Initializing V2.4 Trainer (Index Alignment Fix)...")

# --- ⚡ OPTIMIZATION: HEADLESS PLOTTING ---
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt

# --- ML LIBRARIES ---
try:
    print("   ... Loading TensorFlow & XGBoost ...")
    import tensorflow as tf
    from tensorflow.keras.models import Model
    from tensorflow.keras.layers import Input, Conv2D, MaxPooling2D, Flatten, LSTM, Dense, Concatenate, Dropout
    from tensorflow.keras.optimizers import Adam
    from tensorflow.keras.callbacks import EarlyStopping
    import xgboost as xgb
    from sklearn.preprocessing import RobustScaler
    from sklearn.metrics import accuracy_score
    print("   ✅ Libraries Loaded.")
except ImportError as e:
    print(f"❌ Missing Library: {e}")
    sys.exit()

def fix_and_load_data(path):
    print(f"🧹 Running Smart-Cleaner on {path}...")
    try:
        df = pd.read_csv(path)
    except Exception as e:
        print(f"❌ Read Error: {e}")
        return pd.DataFrame()

    # Ensure Date is string for checking
    if 'Date' not in df.columns: return df
    df['Date_Str'] = df['Date'].astype(str)
    
    # 1. Identify "New" rows (which have dashes like '2026-01-06') vs "Old" rows
    mask_new = df['Date_Str'].str.contains('-')
    
    df_new = df[mask_new].copy()
    df_old = df[~mask_new].copy()
    
    clean_dfs = []
    
    # --- PROCESS OLD DATA (YYYYMMDD + Time Column) ---
    if not df_old.empty and 'Time' in df_old.columns:
        try:
            # Convert Time float to string (e.g. 50100.0 -> '050100')
            df_old = df_old.dropna(subset=['Time'])
            time_str = df_old['Time'].astype(int).astype(str).str.zfill(6)
            
            df_old['Date'] = pd.to_datetime(
                df_old['Date'].astype(str) + ' ' + time_str,
                format='%Y%m%d %H%M%S',
                errors='coerce'
            )
            # Select only the standard 6 columns
            clean_dfs.append(df_old[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']])
        except Exception as e:
            print(f"⚠️ Warning parsing Old Data: {e}")

    # --- PROCESS NEW DATA (Shifted Columns) ---
    if not df_new.empty:
        try:
            # FIX THE SHIFT: Time->Open, Open->High, High->Low, Low->Close, Close->Vol
            df_new['Date'] = pd.to_datetime(df_new['Date'], errors='coerce')
            
            # Capture values before overwriting
            real_open = df_new['Time']
            real_high = df_new['Open']
            real_low = df_new['High']
            real_close = df_new['Low']
            real_vol = df_new['Close']
            
            df_new['Open'] = real_open
            df_new['High'] = real_high
            df_new['Low'] = real_low
            df_new['Close'] = real_close
            df_new['Volume'] = real_vol
            
            clean_dfs.append(df_new[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']])
        except Exception as e:
            print(f"⚠️ Warning parsing New Data: {e}")
            
    if not clean_dfs:
        return pd.DataFrame()
        
    final_df = pd.concat(clean_dfs).sort_values('Date').reset_index(drop=True)
    print(f"✅ Data Cleaned! Total Rows: {len(final_df)}")
    return final_df

# --- CONFIGURATION ---
TRAINING_DATA = r"C:\Data\TrainingHistory.csv"
TRADES_DIR = r"C:\Data\training_data" 
MODEL_PATH_NN = r"C:\Data\hybrid_feature_extractor.h5"
MODEL_PATH_XGB = r"C:\Data\xgb_decision_maker.json"
SCALER_PATH = r"C:\Data\scaler.pkl"

IMG_SIZE = (64, 64)
SEQ_LEN = 50
TP_POINTS = 10.0
SL_POINTS = 10.0
HOLD_PERIOD = 15

logging.basicConfig(level=logging.INFO, format='%(asctime)s - TRAINER - %(message)s')

def prepare_features(df):
    df = df.copy()
    df.columns = df.columns.str.strip()
    if 'Volume' not in df.columns: df['Volume'] = 1.0
    
    cols = ['Close', 'High', 'Low', 'Open', 'Volume']
    for c in cols:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce')
    df.dropna(inplace=True)

    # --- 🛠️ FIX START: Handle Missing 'Time' Column ---
    # If 'Time' is missing, we assume 'Date' holds the full timestamp
    if 'Time' in df.columns:
        # If separate Date and Time columns exist, merge them
        try:
            df['Datetime'] = pd.to_datetime(df['Date'].astype(str) + ' ' + df['Time'].astype(str).str.zfill(6), format='%Y%m%d %H%M%S', errors='coerce')
        except:
            # Fallback if format is weird
            df['Datetime'] = pd.to_datetime(df['Date'])
    else:
        # If no Time column, just use Date
        df['Datetime'] = pd.to_datetime(df['Date'])
    # --- 🛠️ FIX END ---

    # Features
    df['Ret_Close'] = df['Close'].pct_change()
    df['Ret_Vol']   = df['Volume'].pct_change().replace([np.inf, -np.inf], 0)
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['RSI'] = (100 - (100 / (1 + rs))) / 100.0
    
    exp1 = df['Close'].ewm(span=12).mean()
    exp2 = df['Close'].ewm(span=26).mean()
    df['MACD'] = exp1 - exp2
    
    df.dropna(inplace=True)
    return df

def generate_chart_image(df_window):
    if len(df_window) == 0:
        return np.zeros((IMG_SIZE[0], IMG_SIZE[1], 1))

    buf = io.BytesIO()
    fig = plt.figure(figsize=(2, 2), dpi=32)
    ax = fig.add_subplot(111)
    
    vals = df_window['Close'].values
    # Avoid divide by zero
    std_val = np.std(vals)
    if std_val == 0: std_val = 1e-5
        
    norm_vals = (vals - np.mean(vals)) / std_val
    
    ax.plot(norm_vals, color='black', linewidth=2)
    ax.axis('off')
    plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0)
    plt.close(fig)
    plt.close('all') 
    
    buf.seek(0)
    image = tf.io.decode_png(buf.getvalue(), channels=1)
    image = tf.image.resize(image, IMG_SIZE)
    image = image / 255.0
    return image.numpy()

def create_dataset_triple_barrier(df):
    logging.info(f"🏗️ Building Base Dataset (TP: {TP_POINTS} pts)...")
    
    feature_cols = ['Ret_Close', 'Ret_Vol', 'RSI', 'MACD']
    data_values = df[feature_cols].values
    
    highs = df['High'].values
    lows = df['Low'].values
    closes = df['Close'].values
    
    X_visual, X_temporal, y = [], [], []
    
    limit = len(df) - HOLD_PERIOD - 1
    for i in range(SEQ_LEN, limit):
        entry_price = closes[i]
        target_price = entry_price + TP_POINTS
        stop_price = entry_price - SL_POINTS
        
        label = 0 
        for future_i in range(i + 1, i + HOLD_PERIOD + 1):
            if lows[future_i] <= stop_price:
                label = 0
                break
            if highs[future_i] >= target_price:
                label = 1
                break
        
        seq = data_values[i-SEQ_LEN:i]
        X_temporal.append(seq)
        window_raw = df.iloc[i-SEQ_LEN:i]
        img = generate_chart_image(window_raw)
        X_visual.append(img)
        y.append(label)
        
        if i % 5000 == 0:
            print(f"   Processed {i}...", end='\r')

    return np.array(X_visual), np.array(X_temporal), np.array(y)

def process_saved_trade_jsons(df, trades_folder):
    if not os.path.exists(trades_folder): return None, None, None

    json_files = glob.glob(os.path.join(trades_folder, "*.json"))
    if not json_files: return None, None, None

    logging.info(f"💎 Found {len(json_files)} Saved Trades. Parsing...")
    
    feature_cols = ['Ret_Close', 'Ret_Vol', 'RSI', 'MACD']
    data_values = df[feature_cols].values
    
    X_vis, X_temp, y = [], [], []
    valid_count = 0
    
    for jf in json_files:
        try:
            with open(jf, 'r') as f:
                trade_data = json.load(f)
            
            entry_str = trade_data.get('entry_time', '') 
            if not entry_str: continue
            
            dt_obj = pd.to_datetime(entry_str)
            # Find exact minute match
            mask = (df['Datetime'].dt.year == dt_obj.year) & \
                   (df['Datetime'].dt.month == dt_obj.month) & \
                   (df['Datetime'].dt.day == dt_obj.day) & \
                   (df['Datetime'].dt.hour == dt_obj.hour) & \
                   (df['Datetime'].dt.minute == dt_obj.minute)
                   
            match = df[mask]
            if match.empty: continue
                
            idx = match.index[0] # This now maps correctly due to reset_index
            if idx < SEQ_LEN: continue

            # 🛠️ SHAPE GUARD: Ensure sequence is full length
            seq = data_values[idx-SEQ_LEN:idx]
            if seq.shape[0] != SEQ_LEN:
                continue 
            
            if np.isnan(seq).any(): continue

            # --- 🧠 LOGIC FIX: CALCULATE OUTCOME FROM DATA ---
            # We ignore the missing 'estimated_outcome' tag and calculate result manually.
            
            # 1. Identify Entry and Logic
            action = trade_data.get('action', 'FLAT') # Note: main_commander uses "action", not "entry_logic"
            if action not in ['BUY', 'SELL']: continue

            entry_price = df['Close'].iloc[idx]
            
            # 2. Define Targets (Uses the global TP_POINTS/SL_POINTS you just updated)
            # If you want dynamic ATR here, you would calculate it, but fixed is safer for training stability.
            target_price = entry_price + TP_POINTS if action == 'BUY' else entry_price - TP_POINTS
            stop_price = entry_price - SL_POINTS if action == 'BUY' else entry_price + SL_POINTS
            
            outcome_label = 0 # Default to Loss
            
            # 3. Look Ahead (Check the next 15 bars for a win/loss)
            future_highs = df['High'].iloc[idx+1 : idx+HOLD_PERIOD+1].values
            future_lows = df['Low'].iloc[idx+1 : idx+HOLD_PERIOD+1].values
            
            for k in range(len(future_highs)):
                # BUY LOGIC
                if action == 'BUY':
                    if future_lows[k] <= stop_price: # Hit Stop
                        outcome_label = 0
                        break
                    if future_highs[k] >= target_price: # Hit Target
                        outcome_label = 1
                        break
                
                # SELL LOGIC
                elif action == 'SELL':
                    if future_highs[k] >= stop_price: # Hit Stop
                        outcome_label = 0
                        break
                    if future_lows[k] <= target_price: # Hit Target
                        outcome_label = 1
                        break

            # 4. Append Result
            window_raw = df.iloc[idx-SEQ_LEN:idx]
            img = generate_chart_image(window_raw)
            
            X_temp.append(seq)
            X_vis.append(img)
            y.append(outcome_label)
            valid_count += 1
            # ------------------------------------------------
            
        except Exception as e:
            continue

    if valid_count == 0:
        logging.warning("   ⚠️ No valid trades extracted (Check dates/outcomes).")
        return None, None, None

    logging.info(f"💎 Successfully extracted {valid_count} Golden Samples.")
    return np.array(X_vis), np.array(X_temp), np.array(y)

def build_nn_model():
    cnn_input = Input(shape=(IMG_SIZE[0], IMG_SIZE[1], 1))
    x = Conv2D(16, (3, 3), activation='relu')(cnn_input)
    x = MaxPooling2D((2, 2))(x)
    x = Flatten()(x)
    cnn_out = Dense(32, activation='relu')(x)
    
    lstm_input = Input(shape=(SEQ_LEN, 4))
    y = LSTM(32, return_sequences=False)(lstm_input)
    y = Dropout(0.2)(y)
    lstm_out = Dense(32, activation='relu')(y)
    
    combined = Concatenate()([cnn_out, lstm_out])
    z = Dense(32, activation='relu', name='fusion_layer')(combined)
    output = Dense(1, activation='sigmoid')(z)
    
    model = Model(inputs=[cnn_input, lstm_input], outputs=output)
    model.compile(optimizer=Adam(learning_rate=0.001), loss='binary_crossentropy', metrics=['accuracy'])
    return model

def train_pipeline():
    if not os.path.exists(TRAINING_DATA): return

    logging.info("Step 1: Preparing Base Data...")
    
    # --- 🛠️ FIX: USE SMART LOADER ---
    try:
        # Replace the standard pd.read_csv with our smart fixer
        df = fix_and_load_data(TRAINING_DATA)
        
        if df.empty:
            logging.error("❌ Data Frame is empty after cleaning.")
            return

        # Ensure numeric data
        for c in ['Open', 'High', 'Low', 'Close', 'Volume']:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors='coerce')
                
    except Exception as e:
        logging.error(f"❌ CRITICAL LOAD ERROR: {e}")
        return
    # ---------------------------------

    # Trim to last 50k to keep training fast
    if len(df) > 50000: df = df.tail(50000)
    
    df.reset_index(drop=True, inplace=True)
    
    # Prepare Features (Note: fix_and_load_data already handled Date/Time merging)
    df = prepare_features(df)
    
    # ... (Rest of your function remains the same) ...
    
    # 1. BASE TRAINING
    X_vis, X_temp, y = create_dataset_triple_barrier(df)
    
    scaler = RobustScaler()
    orig_shape = X_temp.shape
    X_temp_flat = X_temp.reshape(-1, orig_shape[2])
    X_temp_scaled = scaler.fit_transform(X_temp_flat).reshape(orig_shape)
    with open(SCALER_PATH, 'wb') as f: pickle.dump(scaler, f)

    logging.info("🧠 Phase 1: Training Base Model...")
    nn_model = build_nn_model()
    nn_model.fit([X_vis, X_temp_scaled], y, epochs=10, batch_size=32, validation_split=0.2, verbose=1)
    
    # 2. FINE TUNING (JSONs)
    logging.info("💎 Phase 2: Scanning for Saved JSON Trades...")
    X_gold_vis, X_gold_temp, y_gold = process_saved_trade_jsons(df, TRADES_DIR)
    
    if X_gold_vis is not None and len(X_gold_vis) > 0:
        logging.info("🚀 FINE-TUNING ACTIVE...")
        
        g_shape = X_gold_temp.shape
        # Double check we have data
        if g_shape[0] > 0:
            X_gold_flat = X_gold_temp.reshape(-1, g_shape[2])
            X_gold_scaled = scaler.transform(X_gold_flat).reshape(g_shape)
            
            nn_model.compile(optimizer=Adam(learning_rate=0.0001), loss='binary_crossentropy', metrics=['accuracy'])
            nn_model.fit([X_gold_vis, X_gold_scaled], y_gold, epochs=15, batch_size=4, verbose=1)
            logging.info("✅ Fine-Tuning Complete.")
    
    nn_model.save(MODEL_PATH_NN)
    
    # 3. XGBOOST
    logging.info("🚀 Training XGBoost...")
    extractor = Model(inputs=nn_model.input, outputs=nn_model.get_layer('fusion_layer').output)
    X_features = extractor.predict([X_vis, X_temp_scaled])
    
    xgb_model = xgb.XGBClassifier(n_estimators=100, max_depth=4)
    xgb_model.fit(X_features, y)
    xgb_model.get_booster().save_model(MODEL_PATH_XGB)
    logging.info("✅ Training Pipeline Complete.")

if __name__ == "__main__":
    train_pipeline()