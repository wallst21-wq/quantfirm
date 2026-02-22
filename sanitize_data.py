import pandas as pd
import os

# CONFIG
INPUT_FILE = r"C:\Data\RawDump.csv"
OUTPUT_FILE = r"C:\Data\TrainingHistory.csv"

def sanitize():
    print(f"🧹 READING RAW FILE (NO HEADERS): {INPUT_FILE}")
    if not os.path.exists(INPUT_FILE):
        print("❌ ERROR: RawDump.csv not found.")
        return

    try:
        # 1. Read without assuming a header row (header=None)
        # We manually name the columns: 0=DateTime, 1=Open, 2=High, 3=Low, 4=Close, 5=Volume
        try:
            df = pd.read_csv(INPUT_FILE, sep=';', header=None)
            if df.shape[1] < 2: # Fallback to comma if semi-colon fails
                df = pd.read_csv(INPUT_FILE, sep=',', header=None)
        except:
             df = pd.read_csv(INPUT_FILE, sep=',', header=None)

        # 2. Assign Manual Column Names
        # NinjaTrader Export Format: Date Time; Open; High; Low; Close; Volume
        # Check if we have 6 columns
        if df.shape[1] >= 6:
            df.columns = ['DateTime', 'Open', 'High', 'Low', 'Close', 'Volume']
        else:
            # Sometimes volume is missing or format varies, try basic 5
            df.columns = ['DateTime', 'Open', 'High', 'Low', 'Close']

        print(f"   ℹ️ First Row Check: {df.iloc[0].values}")

        # 3. Create the Clean DataFrame
        new_df = pd.DataFrame()
        
        # Split "20251211 060100" into Date and Time
        # Ensure it's string first
        raw_time = df['DateTime'].astype(str)
        
        new_df['Date'] = raw_time.str.split(' ').str[0]
        new_df['Time'] = raw_time.str.split(' ').str[1]

        # Map the rest
        new_df['Open'] = df['Open']
        new_df['High'] = df['High']
        new_df['Low'] = df['Low']
        new_df['Close'] = df['Close']
        if 'Volume' in df.columns:
            new_df['Volume'] = df['Volume']
        else:
            new_df['Volume'] = 0 # Fill 0 if missing

        # 4. Save
        new_df.to_csv(OUTPUT_FILE, index=False)
        print(f"✅ SUCCESS! Converted {len(new_df)} rows.")
        print(f"   Saved to: {OUTPUT_FILE}")

    except Exception as e:
        print(f"❌ SANITIZE FAILED: {e}")

if __name__ == "__main__":
    sanitize()