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
BILLING_DATASET = os.environ.get("BILLING_DATASET", "billing_export")
BILLING_TABLE = os.environ.get("BILLING_TABLE", "gcp_billing_export_v1_*")

BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_PATH = OUTPUT_DIR / "billing.csv"

OUTPUT_DIR.mkdir(exist_ok=True)

query = f"""
SELECT
  DATE(usage_start_time) AS date,
  CASE
    WHEN EXISTS (
      SELECT 1 FROM UNNEST(labels) AS l
      WHERE l.key = 'workload' AND l.value = 'otter-service'
    ) THEN 'otter-service'
    ELSE 'edx'
  END AS service,
  ROUND(SUM(cost), 2) AS cost
FROM `{PROJECT}.{BILLING_DATASET}.{BILLING_TABLE}`
WHERE DATE(usage_start_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
  AND project.id = '{PROJECT}'
GROUP BY 1, 2
ORDER BY 1
"""

client = bigquery.Client(project=PROJECT)
df = client.query(query).to_dataframe()
df.to_csv(OUTPUT_PATH, index=False)
print(f"Billing data written to {OUTPUT_PATH} ({len(df)} rows)")
