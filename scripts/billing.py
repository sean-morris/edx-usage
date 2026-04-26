import os
import pandas as pd
from pathlib import Path
from google.cloud import bigquery

# ---------------------------------------------------------------------------
# GCP Billing export to BigQuery must be enabled once in the GCP Billing
# console: Billing → Billing export → BigQuery export → Enable.
# Set BILLING_DATASET to the dataset name you configured there.
# The table name follows the pattern:
#   gcp_billing_export_v1_{BILLING_ACCOUNT_ID_WITH_UNDERSCORES}
# ---------------------------------------------------------------------------

PROJECT = "data8x-scratch"
BILLING_DATASET = os.environ.get("BILLING_DATASET", "costs")
BILLING_TABLE = os.environ.get("BILLING_TABLE", "gcp_billing_export_v1_018229_5357DC_756F0D")

BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_PATH = OUTPUT_DIR / "billing.csv"

OUTPUT_DIR.mkdir(exist_ok=True)

query = f"""
SELECT
  DATE(usage_start_time, "America/Los_Angeles") AS date,
  service.description AS service,
  ROUND(SUM(cost + IFNULL(
    (SELECT SUM(c.amount) FROM UNNEST(credits) AS c), 0
  )), 2) AS cost
FROM `{PROJECT}.{BILLING_DATASET}.{BILLING_TABLE}`
WHERE DATE(usage_start_time, "America/Los_Angeles") >= DATE_SUB(
    CURRENT_DATE("America/Los_Angeles"), INTERVAL 30 DAY)
  AND project.id = '{PROJECT}'
GROUP BY 1, 2
ORDER BY 1
"""

client = bigquery.Client(project=PROJECT)
try:
    df = client.query(query).to_dataframe(create_bqstorage_client=False)
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"Billing data written to {OUTPUT_PATH} ({len(df)} rows)")
except Exception as e:
    print(f"WARNING: Could not fetch billing data: {e}")
    print("Writing empty billing CSV and continuing.")
    pd.DataFrame(columns=["date", "service", "cost"]).to_csv(OUTPUT_PATH, index=False)
