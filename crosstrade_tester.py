import requests
import time

# ==========================================
# 🔧 CONFIGURATION (UPDATE THESE!)
# ==========================================
WEBHOOK_URL = "https://app.crosstrade.io/v1/send/Hunm2Ve4/1PG9b8GEukklVI8pnmeT3Q"
API_KEY = "zmHO2C_5QNvtW2wBFfJBbu98f4h5R24YRtkhFjFfSfc"      # 🔑 REQUIRED: Paste your CrossTrade Secret Key here
ACCOUNT_NAME = "Sim101"            # 🏦 REQUIRED: Your NinjaTrader Account Name (e.g., Sim101, Apex, PA-...)

# Test Details
SYMBOL = "MNQ 03-26"
QTY = 1
ACTION = "BUY" # or SELL

def send_test_signal():
    print(f"🔵 Starting CrossTrade 'Plain Text' Connection Test...")
    print(f"   Target: {WEBHOOK_URL}")
    
    # 1. Construct Plain Text Payload (CrossTrade Native Format)
    # Format: key=...; command=PLACE; account=...; instrument=...; action=...; qty=...;
    payload = (
        f"key={API_KEY}; "
        f"command=PLACE; "
        f"account={ACCOUNT_NAME}; "
        f"instrument={SYMBOL}; "
        f"action={ACTION}; "
        f"qty={QTY}; "
        f"order_type=MARKET; "
        f"tif=DAY;"
    )
    
    # 2. Set Headers to Plain Text
    headers = {
        "Content-Type": "text/plain"
    }

    try:
        # 3. Send Request
        print("   ... Sending payload...")
        print(f"   📦 Data: {payload}")
        
        start_time = time.time()
        # Note: Using data=payload instead of json=payload
        response = requests.post(WEBHOOK_URL, data=payload, headers=headers, timeout=10)
        duration = time.time() - start_time
        
        # 4. Analyze Response
        print(f"\n   ⏱️ Latency: {duration:.3f}s")
        print(f"   📡 Status Code: {response.status_code}")
        print(f"   📝 Response: {response.text}")
        
        if response.status_code == 200 or response.status_code == 201:
            if "success" in response.text.lower() or "queued" in response.text.lower():
                print("\n   ✅ SUCCESS: CrossTrade accepted the command.")
                print("   👉 Check NinjaTrader for the 'Market Buy' order.")
            else:
                print("\n   ⚠️ RECEIVED (200 OK) BUT CHECK MESSAGE:")
                print("   The server accepted the request, but read the response text above carefully.")
        else:
            print(f"\n   ❌ FAILED: Server rejected the request.")
            print("   -> Check your API KEY and ACCOUNT NAME.")

    except Exception as e:
        print(f"   ❌ CRITICAL ERROR: {e}")

if __name__ == "__main__":
    send_test_signal()