import os
import sys
import csv
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
sys.path.insert(0, str(Path(__file__).parent))

from edx import get_users

TOKEN = os.environ.get("JUPYTERHUB_TOKEN")
if not TOKEN:
    raise EnvironmentError("JUPYTERHUB_TOKEN environment variable is not set")

SECTIONS = {
    "88E.1": DATA_DIR / "88.1ex" / "ids.csv",
    "88E.2": DATA_DIR / "88.2ex" / "ids.csv",
    "88E.3": DATA_DIR / "88.3ex" / "ids.csv",
    "88B.1": DATA_DIR / "88.1bx" / "ids.csv",
    "88B.2": DATA_DIR / "88.2bx" / "ids.csv",
    "88B.3": DATA_DIR / "88.3bx" / "ids.csv",
    "88C.1": DATA_DIR / "88.1cx" / "ids.csv",
    "88C.2": DATA_DIR / "88.2cx" / "ids.csv",
    "88C.3": DATA_DIR / "88.3cx" / "ids.csv",
}

# Build lookup: course_specific_anon_id -> (user_id, section)
course_specific_to_user = {}
for section_name, path in SECTIONS.items():
    if not path.exists():
        print(f"Skipping {section_name}: {path} not found")
        continue
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            uid = row["User ID"]
            course_specific_id = row["Course Specific Anonymized User ID"]
            course_specific_to_user[course_specific_id] = (uid, section_name)

print(f"Loaded {len(course_specific_to_user)} course-specific ID mappings")

print("Fetching JupyterHub users...")
hub_users = get_users("edx", TOKEN)
print(f"Fetched {len(hub_users)} JupyterHub users")

records = []
unmatched = 0
for user in hub_users:
    name = user.get("name")
    last_activity = user.get("last_activity")
    if name in course_specific_to_user:
        user_id, section = course_specific_to_user[name]
        records.append({"User ID": user_id, "section": section, "last_activity": last_activity})
    else:
        unmatched += 1

print(f"Matched {len(records)} users, {unmatched} unmatched")

ACTIVITY_COLS = [f"{s} last activity" for s in SECTIONS]
df = pd.DataFrame(records)

if df.empty:
    pivot = pd.DataFrame(columns=["User ID"])
else:
    pivot = df.pivot_table(
        index="User ID",
        columns="section",
        values="last_activity",
        aggfunc="max",
    ).reset_index()
    pivot.columns.name = None

    # Strip time from timestamps, keep date only
    for col in pivot.columns:
        if col != "User ID":
            pivot[col] = pivot[col].apply(lambda x: x[:10] if isinstance(x, str) else x)

    # Rename section keys to "88X.Y last activity"
    for section in list(SECTIONS.keys()):
        new_col = f"{section} last activity"
        if section in pivot.columns:
            pivot = pivot.rename(columns={section: new_col})

for col in ACTIVITY_COLS:
    if col not in pivot.columns:
        pivot[col] = "none"
    else:
        pivot[col] = pivot[col].fillna("none")

pivot = pivot[["User ID"] + ACTIVITY_COLS]

output_path = BASE_DIR / "output" / "user_activity.csv"
output_path.parent.mkdir(exist_ok=True)
pivot.to_csv(output_path, index=False)
print(f"Saved {len(pivot)} rows to {output_path}")
print(pivot.head())
