from google import genai
import json
import os

SECRETS_PATH = r"config\secrets.json"
try:
    with open(SECRETS_PATH) as f:
        secrets = json.load(f)
    api_key = secrets.get("gemini_api_key") or secrets.get("GEMINI_API_KEY")

    # Initialize Client
    client = genai.Client(api_key=api_key)

    print("\n🔍 SCANNING GOOGLE MODELS...")
    print("-----------------------------")

    # Simple loop - just print names
    for m in client.models.list():
        print(f"✅ FOUND: {m.name}")

    print("-----------------------------")
    print("Scan Complete.\n")

except Exception as e:
    print(f"❌ ERROR: {e}")