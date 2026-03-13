import pandas as pd
from pathlib import Path
from datetime import date

BASE_DIR = Path(__file__).parent.parent

df = pd.read_csv(BASE_DIR / "output" / "user_activity.csv")

courses = {
    "88.1": "88.1 last activity",
    "88.2": "88.2 last activity",
    "88.3": "88.3 last activity",
}

# Current month as "YYYY-MM"
current_month = date.today().strftime("%Y-%m")

# Count users whose last_activity falls within the current calendar month
row = {"month-year": current_month}
for course, col in courses.items():
    active_this_month = df[df[col].str.startswith(current_month, na=False)]
    row[f"{course} users"] = len(active_this_month)

print(f"Current month ({current_month}): {row}")

# Load the persistent historical record and upsert current month
data_path = BASE_DIR / "data" / "monthly_activity.csv"
data_path.parent.mkdir(exist_ok=True)

if data_path.exists():
    history = pd.read_csv(data_path, dtype=str)
else:
    history = pd.DataFrame(columns=["month-year", "88.1 users", "88.2 users", "88.3 users"])

# Upsert: replace existing row for this month or append
history = history[history["month-year"] != current_month]
history = pd.concat([history, pd.DataFrame([row])], ignore_index=True)
history = history.sort_values("month-year").reset_index(drop=True)

history.to_csv(data_path, index=False)
print(f"Saved {len(history)} rows to {data_path}")
print(history.to_string(index=False))
