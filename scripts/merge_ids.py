import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

DATA_DIR = BASE_DIR / "data"

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

merged = None

for col_name, path in SECTIONS.items():
    if not path.exists():
        print(f"Skipping {col_name}: {path} not found")
        continue
    df = pd.read_csv(path, usecols=["User ID", "Anonymized User ID"])
    df = df.rename(columns={"Anonymized User ID": col_name})
    if merged is None:
        merged = df
    else:
        merged = merged.merge(df, on="User ID", how="outer")

if merged is None:
    merged = pd.DataFrame(columns=["User ID"])

output_path = BASE_DIR / "output" / "merged_ids.csv"
output_path.parent.mkdir(exist_ok=True)
merged = merged.fillna("none")
merged.to_csv(output_path, index=False)
print(f"Saved {len(merged)} rows to {output_path}")
