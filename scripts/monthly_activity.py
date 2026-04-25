import pandas as pd
from pathlib import Path
from datetime import date

BASE_DIR = Path(__file__).parent.parent

df = pd.read_csv(BASE_DIR / "output" / "user_activity.csv")

SECTIONS = ["88E.1", "88E.2", "88E.3", "88B.1", "88B.2", "88B.3", "88C.1", "88C.2", "88C.3"]
EXPECTED_COLS = ["month-year"] + [f"{s} users" for s in SECTIONS]

current_month = date.today().strftime("%Y-%m")

row = {"month-year": current_month}
for section in SECTIONS:
    col = f"{section} last activity"
    if col in df.columns:
        row[f"{section} users"] = len(df[df[col].str.startswith(current_month, na=False)])
    else:
        row[f"{section} users"] = 0

print(f"Current month ({current_month}): {row}")

data_path = BASE_DIR / "data" / "monthly_activity.csv"
data_path.parent.mkdir(exist_ok=True)

if data_path.exists():
    history = pd.read_csv(data_path, dtype=str)
    # Migrate old section names (88.1/2/3 -> 88E.1/2/3)
    history = history.rename(columns={
        "88.1 users": "88E.1 users",
        "88.2 users": "88E.2 users",
        "88.3 users": "88E.3 users",
    })
    # Add any missing new-course columns
    for col in EXPECTED_COLS[1:]:
        if col not in history.columns:
            history[col] = "0"
else:
    history = pd.DataFrame(columns=EXPECTED_COLS)

history = history[history["month-year"] != current_month]
history = pd.concat([history, pd.DataFrame([row])], ignore_index=True)
history = history.sort_values("month-year").reset_index(drop=True)

history.to_csv(data_path, index=False)
print(f"Saved {len(history)} rows to {data_path}")
print(history.to_string(index=False))
