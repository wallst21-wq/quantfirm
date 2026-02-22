import os
import sys
import logging
import numpy as np
import pandas as pd
import io
import pickle

# --- ⚡ OPTIMIZATION ---
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt

try:
    import tensorflow as tf
    from tensorflow.keras.models import Model, load_model
    import xgboost as xgb
except ImportError:
    pass # Assume installed

# --- CONFIGURATION ---
MARKET_DATA = r"C:\Data\MarketData.csv"
MODEL_PATH_NN = r"C:\Data\hybrid_feature_extractor.h5"
MODEL_PATH_XGB = r"C:\Data\xgb_decision_maker.json"
SCALER_PATH = r"C:\Data\scaler.pkl"
IMG_SIZE = (64, 64)
SEQ_LEN = 50

class HybridPredictor:
    def __init__(self):
        self.nn_model = None
        self.xgb_model = None
        self.extractor = None
        self.scaler = None
        self.load_artifacts()

    def load_artifacts(self):
        """ Loads NN, XGB, and Scaler """
        try:
            if os.path.exists(MODEL_PATH_NN) and os.path.exists(MODEL_PATH_XGB):
                logging.info("🧠 Loading Hybrid Engine (NN + XGB)...")
                
                # Load NN
                full_model = load_model(MODEL_PATH_NN)
                # Reconstruct Extractor (Input -> Fusion Layer)
                self.extractor = Model(inputs=full_model.input, outputs=full_model.get_layer('fusion_layer').output)
                
                # Load XGB
                self.xgb_model = xgb.XGBClassifier()
                self.xgb_model.load_model(MODEL_PATH_XGB)
                
                # Load Scaler
                with open(SCALER_PATH, 'rb') as f:
                    self.scaler = pickle.load(f)
                    
                logging.info("✅ Hybrid Engine Ready.")
            else:
                logging.warning("⚠️ Training artifacts not found. Run 'model_trainer.py' first.")
        except Exception as e:
            logging.error(f"Init Error: {e}")

    # ... [Insert Manual Indicator Functions: rsi, bb, macd here if needed, same as trainer] ...
    # For brevity, reusing the raw calculation logic inside prep

    def generate_market_image(self, df_window):
        # Same generating logic as Trainer
        buf = io.BytesIO()
        fig = plt.figure(figsize=(2, 2), dpi=32)
        ax = fig.add_subplot(111)
        ax.plot(df_window['Close'].values, color='black')
        ma = df_window['Close'].rolling(10).mean().values
        ax.plot(ma, color='gray', alpha=0.5)
        ax.axis('off')
        plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0)
        plt.close(fig)
        plt.close('all')
        buf.seek(0)
        img = tf.io.decode_png(buf.getvalue(), channels=1)
        img = tf.image.resize(img, IMG_SIZE) / 255.0
        return tf.expand_dims(img, axis=0) # (1, 64, 64, 1)

    def get_market_prediction(self):
        if not self.xgb_model or not self.extractor:
            return "NEUTRAL", 0 # Fallback if not trained
            
        try:
            df = pd.read_csv(MARKET_DATA)
            if len(df) < SEQ_LEN + 20: return "NEUTRAL", 0
            
            # --- PREP DATA LIVE ---
            # (Requires calculating indicators on the fly using same logic as trainer)
            # For robustness in V1, we assume CSV has raw data and we perform minimal transform
            # In V2, we ensure indicators are synced. 
            
            window = df.tail(SEQ_LEN).copy()
            # Note: For production, we need to ensure the Scaler input shape matches exactly.
            # This requires recreating the indicator columns in the engine. 
            # (Assuming you add the indicator functions here too).
            
            # Placeholder for safe return while you run training
            return "NEUTRAL", 0 
            
        except Exception as e:
            return "NEUTRAL", 0

# Global Instance
engine = HybridPredictor()
def get_market_prediction():
    return engine.get_market_prediction()