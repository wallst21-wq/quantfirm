import os
import glob
import json
import pandas as pd
import predictive_engine as brain

# --- CONFIGURATION ---
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
TRAINING_DATA_DIR = os.path.join(ROOT_DIR, 'training_data')

def run_weekend_training():
    print("🧠 STARTING WEEKEND RETRAINING PROTOCOL...")
    
    # 1. Analyze Lessons Learned
    files = glob.glob(os.path.join(TRAINING_DATA_DIR, "*.json"))
    wins = 0
    losses = 0
    
    print(f"    Scanning {len(files)} trade records...")
    for f in files:
        try:
            with open(f, 'r') as jf:
                data = json.load(jf)
                outcome = data.get('estimated_outcome', 'UNKNOWN')
                if outcome == 'WIN': wins += 1
                if outcome == 'LOSS': losses += 1
        except: pass
    
    print(f"    Performance Review: {wins} Wins / {losses} Losses")
    
    # 2. Trigger Mathematical Retraining
    # This forces the Hybrid Engine to re-read the CSV and find new patterns
    print("    Re-calibrating LSTM + XGBoost weights based on latest data...")
    
    # Force Retrain flag tells the engine to ignore saved models and rebuild
    brain.FORCE_RETRAIN = True 
    brain.train_hybrid_model()
    
    print("✅ WEEKEND RETRAINING COMPLETE. The AI Oracle is now smarter.")

if __name__ == "__main__":
    run_weekend_training()
    input("Press Enter to exit...")