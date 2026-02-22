import os

filename = "main_commander.py"

print(f"🔧 Scanning {filename} for syntax errors...")

try:
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    fixed_count = 0
    
    for i, line in enumerate(lines):
        # DETECT THE BUG:
        # A 'save_mission_state()' that is only indented 4 spaces (it should be 8)
        if line.startswith("    save_mission_state()") and "def " not in line:
            print(f"   ⚠️ Found misalignment at line {i+1}. Fixing...")
            new_lines.append("        save_mission_state()\n") # Push to 8 spaces
            fixed_count += 1
        else:
            new_lines.append(line)

    if fixed_count > 0:
        with open(filename, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print(f"✅ SUCCESS: Repaired {fixed_count} indentation errors.")
        print("   You can now run 'python main_commander.py'")
    else:
        print("✅ No errors found. The file looks correct.")

except Exception as e:
    print(f"❌ Error: {e}")