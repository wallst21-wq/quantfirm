import pandas as pd
import os
import predictive_engine as brain

# --- CONFIG ---
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
# Point this to your BIG 180-Day file
SOURCE_FILE = r"C:\Data\TrainingHistory.csv" 
CLEAN_FILE = r"C:\Data\Cleaned_History.csv"

def run_lobotomy():
    print("🧠 STARTING 'LOBOTOMY' PROTOCOL...")
    
    # 1. Load the "Poisoned" History (Includes Today)
    if not os.path.exists(SOURCE_FILE):
        print(f"❌ ERROR: Could not find {SOURCE_FILE}")
        return

    print(f"    Loading full history from {SOURCE_FILE}...")
    df = pd.read_csv(SOURCE_FILE)
    original_len = len(df)
    
    # 2. Chop off the last 3 Days (approx 4500-5000 mins)
    # This removes the "Answer Key" for today's session
    CUTOFF = 5000 
    
    if original_len > CUTOFF:
        df_clean = df.iloc[:-CUTOFF] # Keep everything EXCEPT the last 5000 rows
        print(f"    ✂️ REMOVING last {CUTOFF} rows (Today's Data)...")
        print(f"    Old Size: {original_len} -> New Size: {len(df_clean)}")
    else:
        print("    ⚠️ File too small to trim. Using as is (Not recommended).")
        df_clean = df

    # 3. Save the "Clean" File
    df_clean.to_csv(CLEAN_FILE, index=False)
    print(f"    ✅ Clean file saved to: {CLEAN_FILE}")
    
    # 4. Point the Brain to the Clean File TEMPORARILY
    # We hack the module's variable directly
    brain.DATA_FILE = CLEAN_FILE
    brain.FORCE_RETRAIN = True
    
    # 5. Train
    print("    🔄 Retraining Hybrid Brain on Clean Data...")
    brain.train_hybrid_model()
    
    print("✅ LOBOTOMY COMPLETE. The AI has forgotten today's price action.")
    print("👉 YOU MUST NOW RESTART 'main_commander.py' to load the new brain.")

if __name__ == "__main__":
    run_lobotomy()
    input("Press Enter to exit...")