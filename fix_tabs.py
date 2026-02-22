import sys
import os

filename = "main_commander.py"

try:
    # 🛠️ FIX: Added encoding='utf-8' to handle Emojis (🚀, 🎯)
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()

    # The Magic Fix: Turn every Tab into 4 Spaces
    new_content = content.replace('\t', '    ')

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"✅ SUCCESS: Converted all tabs to spaces in {filename}")
    print("   You can now run 'python main_commander.py'")

except Exception as e:
    print(f"❌ Error: {e}")