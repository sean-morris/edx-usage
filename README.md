# 88x JupyterHub Activity Dashboard

Fetches JupyterHub activity data for 88.1, 88.2, and 88.3 and builds a static HTML dashboard showing monthly active users and per-student last activity.

## Repository layout

```
88.1ex/ids.csv          # edX export: User ID, Anonymized User ID, Course Specific Anonymized User ID
88.2ex/ids.csv
88.3ex/ids.csv
scripts/
  merge_ids.py          # merges ids.csv files across courses -> output/merged_ids.csv
  merge_activity.py     # fetches JupyterHub users via API, maps to User IDs -> output/user_activity.csv
  monthly_activity.py   # aggregates user_activity.csv by month -> output/monthly_activity.csv
  build_dashboard.py    # renders output CSVs into dashboard/index.html
  edx.py                # JupyterHub API helper
data/
  monthly_activity.csv  # persistent historical record, committed and upserted each run
output/                 # generated, not committed
docs/index.html         # generated static dashboard (served via GitHub Pages)
```

## Setup

1. Create a `.env` file in the repo root:
   ```
   JUPYTERHUB_TOKEN=<your token>
   ```

2. Install dependencies:
   ```zsh
   conda env create -f environment.yaml
   conda activate edx-usage
   ```

## Running

```zsh
python main.py
```

This runs all pipeline steps in order and writes `dashboard/index.html`.

## Input CSVs

Each course directory needs an `ids.csv` exported from edX with columns:
- `User ID`
- `Anonymized User ID`
- `Course Specific Anonymized User ID`

No `users.csv` or other personally identifiable data is required or used.
