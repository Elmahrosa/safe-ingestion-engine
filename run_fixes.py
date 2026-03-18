import sys
import os
import subprocess

# Force UTF-8 encoding for Windows
os.environ['PYTHONIOENCODING'] = 'utf-8'

# List of fix scripts
fixes = [
    'fix_01_hmac_consistency.py',
    'fix_02_domain_concurrency_race.py', 
    'fix_03_metrics_auth.py',
    'fix_04_dashboard_sqli.py',
    'fix_05_trial_credits_sync.py',
    'fix_06_redirects_stream.py',
    'fix_07_security_event_flag.py',
    'fix_08_rotate_api_keys.py',
    'fix_09_mcp_status_case.py',
    'fix_10_complete_ready_to_apply.py'
]

for fix in fixes:
    if os.path.exists(fix):
        print(f"Running {fix}...")
        try:
            result = subprocess.run([sys.executable, fix], 
                                  capture_output=True, 
                                  text=True, 
                                  encoding='utf-8')
            print(result.stdout)
            if result.stderr:
                print(f"Error: {result.stderr}")
        except Exception as e:
            print(f"Failed to run {fix}: {e}")
    else:
        print(f"File {fix} not found")
