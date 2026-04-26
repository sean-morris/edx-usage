"""
Reconstructs daily peak concurrent users from JupyterHub Cloud Logging events.

Queries server spawn/stop/cull events over the last 30 days and computes the
peak number of simultaneously running user servers per day.
Writes to data/concurrent_users.csv.
"""

import re
import json
import subprocess
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta, timezone
from collections import defaultdict

PROJECT = "data8x-scratch"
BASE_DIR = Path(__file__).parent.parent
OUTPUT_PATH = BASE_DIR / "data" / "concurrent_users.csv"

RE_START = re.compile(r"Server (\w{20,}) is ready")
RE_STOP  = re.compile(r"User (\w{20,}) server stopped")
RE_CULL  = re.compile(r"Culling server (\w{20,})")


def fetch_log_entries(days=30):
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    log_filter = (
        'resource.type="k8s_container" '
        'resource.labels.namespace_name="edx-prod" '
        'resource.labels.container_name="hub" '
        '(textPayload=~"is ready" OR textPayload=~"server stopped" OR textPayload=~"Culling server") '
        f'timestamp>="{since}"'
    )
    result = subprocess.run(
        ["gcloud", "logging", "read", log_filter,
         "--project", PROJECT, "--limit", "50000", "--format", "json"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"WARNING: gcloud logging read failed: {result.stderr[:200]}")
        return []
    return json.loads(result.stdout or "[]")


def parse_event(entry):
    payload = entry.get("textPayload", "") or entry.get("jsonPayload", {}).get("message", "")
    ts_str  = entry.get("timestamp", "")
    try:
        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except Exception:
        return None

    m = RE_START.search(payload)
    if m:
        return (ts, m.group(1), "start")
    m = RE_STOP.search(payload)
    if m:
        return (ts, m.group(1), "stop")
    m = RE_CULL.search(payload)
    if m:
        return (ts, m.group(1), "stop")
    return None


def compute_daily_peaks(events):
    """
    Walk events in chronological order, maintain active server set,
    record peak concurrent count per calendar day (UTC).
    Sessions that span midnight carry into the next day correctly.
    """
    active = set()
    daily_peaks = defaultdict(int)

    for ts, user, event_type in sorted(events, key=lambda x: x[0]):
        if event_type == "start":
            active.add(user)
        else:
            active.discard(user)
        day = ts.date()
        daily_peaks[day] = max(daily_peaks[day], len(active))

    return daily_peaks


def main():
    print("Fetching server lifecycle events from Cloud Logging (last 30 days)...")
    entries = fetch_log_entries(days=30)
    print(f"  {len(entries)} log entries fetched")

    events = [e for entry in entries if (e := parse_event(entry))]
    print(f"  {len(events)} server lifecycle events parsed")

    if not events:
        print("No events found — writing no changes.")
        return

    daily_peaks = compute_daily_peaks(events)

    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    existing = (
        pd.read_csv(OUTPUT_PATH)
        if OUTPUT_PATH.exists()
        else pd.DataFrame(columns=["date", "peak_concurrent"])
    )

    new_rows = pd.DataFrame([
        {"date": str(d), "peak_concurrent": peak}
        for d, peak in sorted(daily_peaks.items())
    ])

    merged = pd.concat(
        [existing[~existing["date"].isin(new_rows["date"])], new_rows],
        ignore_index=True
    ).sort_values("date").reset_index(drop=True)

    merged.to_csv(OUTPUT_PATH, index=False)
    print(f"Saved {len(merged)} rows to {OUTPUT_PATH}")
    print(merged.tail(14).to_string(index=False))


if __name__ == "__main__":
    main()
