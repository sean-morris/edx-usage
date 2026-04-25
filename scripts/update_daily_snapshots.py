"""
Record daily active-user and running-server snapshots.
Appends one row per day to data/daily_snapshots.csv.

'active' counts users whose last_activity for any section equals today.
'running_servers' is the count of JupyterHub users with at least one active server,
used as a proxy for peak concurrent users at time of pipeline run.
"""
import os
import sys
import pandas as pd
from pathlib import Path
from datetime import date
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
load_dotenv(Path(__file__).parent.parent / ".env")

BASE_DIR = Path(__file__).parent.parent
ACTIVITY_PATH = BASE_DIR / "output" / "user_activity.csv"
SNAPSHOT_PATH = BASE_DIR / "data" / "daily_snapshots.csv"

SECTIONS = ["88E.1", "88E.2", "88E.3", "88B.1", "88B.2", "88B.3", "88C.1", "88C.2", "88C.3"]

today_str = date.today().isoformat()
TOKEN = os.environ.get("JUPYTERHUB_TOKEN")

# Count running servers from JupyterHub API
running_servers = 0
if TOKEN:
    try:
        from edx import get_users
        hub_users = get_users("edx", TOKEN)
        running_servers = sum(1 for u in hub_users if u.get("servers"))
        print(f"Running servers: {running_servers}")
    except Exception as e:
        print(f"WARNING: Could not count running servers: {e}")
else:
    print("WARNING: JUPYTERHUB_TOKEN not set, running_servers will be 0")

# Count users active today per section
activity = pd.read_csv(ACTIVITY_PATH)
row: dict = {"date": today_str, "running_servers": running_servers}
for section in SECTIONS:
    col = f"{section} last activity"
    count = int((activity[col] == today_str).sum()) if col in activity.columns else 0
    row[f"{section} active"] = count

print(f"Snapshot: {row}")

# Upsert today's row
snapshots = pd.read_csv(SNAPSHOT_PATH) if SNAPSHOT_PATH.exists() else pd.DataFrame()
if "date" in snapshots.columns:
    snapshots = snapshots[snapshots["date"] != today_str]
snapshots = pd.concat([snapshots, pd.DataFrame([row])], ignore_index=True)
snapshots = snapshots.sort_values("date").reset_index(drop=True)

SNAPSHOT_PATH.parent.mkdir(exist_ok=True)
snapshots.to_csv(SNAPSHOT_PATH, index=False)
print(f"Saved {len(snapshots)} rows to {SNAPSHOT_PATH}")
