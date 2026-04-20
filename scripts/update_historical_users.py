"""
Compute the current month's 30-day active user count from user_activity.csv
and upsert it into data/hub_historical_users.csv.

'Active in last 30 days' = any last_activity date within 30 days of today.
A user only needs to be active in one course to count.
"""
import pandas as pd
from pathlib import Path
from datetime import date, timedelta

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
ACTIVITY_PATH = BASE_DIR / "output" / "user_activity.csv"
HISTORICAL_PATH = DATA_DIR / "hub_historical_users.csv"

today = date.today()
cutoff_30d = today - timedelta(days=30)
cutoff_24h = today - timedelta(days=1)
current_month = today.strftime("%Y-%m")

activity = pd.read_csv(ACTIVITY_PATH)

activity_cols = [c for c in activity.columns if "last activity" in c]

# Parse activity columns as datetimes (non-dates become NaT)
parsed = activity[activity_cols].apply(
    lambda col: pd.to_datetime(col, format="%Y-%m-%d", errors="coerce")
)

# Most recent activity across all courses for each user
most_recent = parsed.max(axis=1).dt.date

active_30d = int((most_recent >= cutoff_30d).sum())
active_24h = int((most_recent >= cutoff_24h).sum())

hist = pd.read_csv(HISTORICAL_PATH)

# Upsert current month row
if current_month in hist["month"].values:
    hist.loc[hist["month"] == current_month, "active_users_24h"] = active_24h
    hist.loc[hist["month"] == current_month, "active_users_30d"] = active_30d
    action = "updated"
else:
    new_row = pd.DataFrame([{
        "month": current_month,
        "active_users_24h": active_24h,
        "active_users_30d": active_30d,
    }])
    hist = pd.concat([hist, new_row], ignore_index=True)
    action = "appended"

hist.to_csv(HISTORICAL_PATH, index=False)
print(f"Historical users {action} for {current_month}: "
      f"{active_24h} active 24h, {active_30d} active 30d")
