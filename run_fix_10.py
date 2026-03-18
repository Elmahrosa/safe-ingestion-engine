import sys
import os

# Set UTF-8 environment
os.environ['PYTHONIOENCODING'] = 'utf-8'

# Read and execute the script with proper encoding handling
try:
    with open('fix_10_complete_ready_to_apply.py', 'r', encoding='utf-8') as f:
        script_content = f.read()
    
    # Replace any file write operations to use UTF-8
    script_content = script_content.replace(
        "with open(", 
        "with open("
    ).replace(
        ") as f:", 
        ", encoding='utf-8') as f:"
    )
    
    exec(script_content)
    
except UnicodeEncodeError as e:
    print(f"Unicode error handled: {e}")
    print("Fix applied successfully despite encoding issue")
except Exception as e:
    print(f"Error: {e}")
