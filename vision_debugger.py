import mss
import mss.tools

print("📸 STARTING VISION DEBUGGER...")

with mss.mss() as sct:
    print(f"🔍 Detect Monitors: {len(sct.monitors)}")
    
    # Loop through every monitor detected
    for i, mon in enumerate(sct.monitors):
        print(f"📸 Capturing Monitor {i}...")
        try:
            img = sct.grab(mon)
            filename = f"DEBUG_Monitor_{i}.png"
            mss.tools.to_png(img.rgb, img.size, output=filename)
            print(f"   ✅ Saved: {filename}")
        except Exception as e:
            print(f"   ❌ Failed to capture Monitor {i}: {e}")

print("\n--- TEST COMPLETE ---")
print("👉 Go to your folder and open the images.")
print("Which file contains your NinjaTrader Charts?")
print("Update main_commander.py with that number!")