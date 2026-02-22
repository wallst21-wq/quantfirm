from crosstrade_client import CrossTradeClient
import json
import os

# Load Secrets
SECRETS_PATH = r"C:\Users\Administrator\.gemini\antigravity\scratch\Quant_Firm_Root\config\secrets.json"

with open(SECRETS_PATH) as f:
    secrets = json.load(f)

# Initialize Bridge
api_key = secrets.get("crosstrade_api_key") or secrets.get("CROSSTRADE_API_KEY")
client = CrossTradeClient(api_key, "N/A")

print(f"🔌 Connecting with Key: {api_key[:5]}...*****")
print("🔫 FIRING TEST SHOT (Sim101)...")

# FORCE FIRE
response = client.send_signal(
    symbol="NQ 03-26",  # Ensure this matches your NinjaTrader Chart
    action="BUY",
    quantity=1,
    order_type="MARKET"
)

print(f"✅ Signal Sent! Response: {response}")
print("👀 CHECK CROSSTRADE APP 'Signals Received' COUNTER NOW.")