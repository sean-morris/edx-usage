import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent / "scripts"

steps = [
    ("Merging IDs across courses...",        SCRIPTS_DIR / "merge_ids.py"),
    ("Fetching JupyterHub activity...",       SCRIPTS_DIR / "merge_activity.py"),
    ("Building monthly activity summary...", SCRIPTS_DIR / "monthly_activity.py"),
    ("Loading billing data...",              SCRIPTS_DIR / "billing.py"),
    ("Updating historical user counts...",   SCRIPTS_DIR / "update_historical_users.py"),
    ("Recording daily snapshot...",          SCRIPTS_DIR / "update_daily_snapshots.py"),
    ("Building dashboard...",                SCRIPTS_DIR / "build_dashboard.py"),
]

for label, script in steps:
    print(f"\n{'='*50}")
    print(f"  {label}")
    print(f"{'='*50}")
    result = subprocess.run([sys.executable, str(script)], check=False)
    if result.returncode != 0:
        print(f"\nERROR: {script.name} failed with exit code {result.returncode}. Aborting.")
        sys.exit(result.returncode)

print("\nAll done.")
