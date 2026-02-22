import time
import os
import sys
import logging
import json
import numpy as np
import pandas as pd
import io
import pickle

# --- ⚡ OPTIMIZATION: HEADLESS PLOTTING ---
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt

# --- ML LIBRARIES ---
try:
    # Suppress TF Warnings
    os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
    
    import tensorflow as tf
    from tensorflow.keras.models import load_model, Model
    import xgboost as xgb
    from sklearn.preprocessing import RobustScaler
except ImportError as e:
    print(f"❌ Missing Library: {e}")
    sys.exit()

# --- CONFIGURATION ---
MARKET_DATA_FILE = r"C:\Data\MarketData.csv"
MODEL_NN_PATH = r"C:\Data\hybrid_feature_extractor.h5"
MODEL_XGB_PATH = r"C:\Data\xgb_decision_maker.json"
SCALER_PATH = r"C:\Data\scaler.pkl"

IMG_SIZE = (64, 64)
SEQ_LEN = 50

# Confidence Threshold (Only trade if AI is > 60% sure)
CONFIDENCE_THRESHOLD = 0.60 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - COMMANDER - %(message)s')

def load_system():
    logging.info("🔵 Initializing AI Commander...")
    
    if not os.path.exists(MODEL_NN_PATH) or not os.path.exists(MODEL_XGB_PATH):
        logging.error("❌ Models not found! Run 'model_trainer.py' first.")
        sys.exit()
        
    logging.info("   ... Loading Neural Network ...")
    nn_model = load_model(MODEL_NN_PATH)
    
    logging.info("   ... Loading XGBoost ...")
    xgb_model = xgb.Booster()
    xgb_model.load_model(MODEL_XGB_PATH)
    
    logging.info("   ... Loading Scaler ...")
    with open(SCALER_PATH, 'rb') as f:
        scaler = pickle.load(f)
        
    logging.info("✅ System Online.")
    return nn_model, xgb_model, scaler

def prepare_live_data(df):
    """ Matches the exact preprocessing of V2.4 Trainer """
    df = df.copy()
    df.columns = df.columns.str.strip()
    
    # 1. Synthesize Volume if missing (Live data might lag on Vol)
    if 'Volume' not in df.columns: df['Volume'] = 1.0
    
    # 2. Type Conversion
    cols = ['Close', 'High', 'Low', 'Open', 'Volume']
    for c in cols:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce')
    
    # 3. Features
    df['Ret_Close'] = df['Close'].pct_change()
    df['Ret_Vol']   = df['Volume'].pct_change().replace([np.inf, -np.inf], 0)
    
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['RSI'] = (100 - (100 / (1 + rs))) / 100.0
    
    # MACD
    exp1 = df['Close'].ewm(span=12).mean()
    exp2 = df['Close'].ewm(span=26).mean()
    df['MACD'] = exp1 - exp2
    
    # Drop NaNs created by indicators
    df.dropna(inplace=True)
    return df

def generate_chart_image(df_window):
    """ Matches V2.4 Image Generation """
    buf = io.BytesIO()
    fig = plt.figure(figsize=(2, 2), dpi=32)
    ax = fig.add_subplot(111)
    
    vals = df_window['Close'].values
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

def get_latest_prediction(nn_model, xgb_model, scaler):
    # 1. Read Data
    try:
        # Read only last 100 lines to be fast
        with open(MARKET_DATA_FILE, "r") as f:
            q = collections.deque(f, 100)
        df = pd.read_csv(io.StringIO(''.join(q)), header=None)
        
        # ✅ FIX: Removed "Time" to match your NinjaTrader format (Date+Time is one column)
        if len(df.columns) >= 6:
            df.columns = ["Date", "Open", "High", "Low", "Close", "Volume"][:len(df.columns)]
            
            # Helper: Combine Date/Time if needed, or just convert
            # Since your file has one combined column, just convert it:
            df['Date'] = pd.to_datetime(df['Date'])
            
            # Make sure numbers are numbers (fixes any string glitches)
            cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            for c in cols:
                df[c] = pd.to_numeric(df[c], errors='coerce')

    except Exception as e:
        # Fallback for testing if file acts up
        try:
             df = pd.read_csv(MARKET_DATA_FILE).tail(100)
        except:
             print(f"❌ Data Read Error: {e}")
             return None
             
    # ... rest of the function (calculations) ...
    # (Make sure to include the rest of your function code here if it wasn't pasted above)

    # 2. Preprocess
    df = prepare_live_data(df)
    
    if len(df) < SEQ_LEN:
        print(f"   Waiting for data... ({len(df)}/{SEQ_LEN} bars)", end='\r')
        return None

    # 3. Extract last sequence
    last_seq = df.iloc[-SEQ_LEN:]
    
    # 4. Prepare Features (Temporal)
    feature_cols = ['Ret_Close', 'Ret_Vol', 'RSI', 'MACD']
    raw_seq = last_seq[feature_cols].values
    
    # Scale (Using the Pickle Scaler)
    # Reshape for single sample: (1, 50, 4)
    # Scaler expects (n_samples, n_features) so we flatten, scale, reshape
    flat_seq = raw_seq.reshape(-1, 4) 
    scaled_flat = scaler.transform(flat_seq)
    scaled_seq = scaled_flat.reshape(1, SEQ_LEN, 4)
    
    # 5. Prepare Features (Visual)
    img = generate_chart_image(last_seq)
    img_input = img.reshape(1, IMG_SIZE[0], IMG_SIZE[1], 1)
    
    # 6. INFERENCE: Neural Network
    # We need the INTERMEDIATE output (Meta-Features), not the final sigmoid
    # Re-construct the extractor part
    extractor = Model(inputs=nn_model.input, outputs=nn_model.get_layer('fusion_layer').output)
    meta_features = extractor.predict([img_input, scaled_seq], verbose=0)
    
    # 7. INFERENCE: XGBoost
    dtest = xgb.DMatrix(meta_features)
    prob_up = xgb_model.predict(dtest)[0] # Probability of Class 1 (UP)
    
    return prob_up

import collections

def main_loop():
    nn_model, xgb_model, scaler = load_system()
    
    print("\n🟢 LIVE COMMANDER ACTIVE. Watching markets...")
    print(f"   Target: > {CONFIDENCE_THRESHOLD*100}% Confidence\n")
    
    last_processed_time = 0
    
    while True:
        try:
            # Check modification time to see if new bar arrived
            mod_time = os.path.getmtime(MARKET_DATA_FILE)
            if mod_time != last_processed_time:
                
                prob_up = get_latest_prediction(nn_model, xgb_model, scaler)
                
                if prob_up is not None:
                    # Logic
                    signal = "FLAT"
                    color = "\033[90m" # Grey
                    
                    if prob_up > CONFIDENCE_THRESHOLD:
                        signal = "🚀 BUY SIGNAL"
                        color = "\033[92m" # Green
                    elif prob_up < (1.0 - CONFIDENCE_THRESHOLD):
                        signal = "🔻 SELL SIGNAL"
                        color = "\033[91m" # Red
                    
                    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                    print(f"[{timestamp}] Probability UP: {prob_up:.2%} | {color}{signal}\033[0m")
                
                last_processed_time = mod_time
            
            time.sleep(1) # Check every second
            
        except KeyboardInterrupt:
            print("\n🔴 Commander shutting down.")
            break
        except Exception as e:
            logging.error(f"Loop Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    import datetime
    main_loop()