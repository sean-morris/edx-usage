import json
import pandas as pd
from pathlib import Path
from datetime import date

BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output"
DATA_DIR = BASE_DIR / "data"
DASHBOARD_DIR = BASE_DIR / "docs"

monthly = pd.read_csv(DATA_DIR / "monthly_activity.csv")
activity = pd.read_csv(OUTPUT_DIR / "user_activity.csv")
billing = pd.read_csv(OUTPUT_DIR / "billing.csv", parse_dates=["date"])
historical = pd.read_csv(DATA_DIR / "hub_historical_users.csv")

monthly_json = json.dumps(monthly.to_dict(orient="records"))
activity_json = json.dumps(activity.fillna("none").to_dict(orient="records"))
historical_months_json = json.dumps(historical["month"].tolist())
historical_30d_json = json.dumps(historical["active_users_30d"].tolist())
historical_24h_json = json.dumps(historical["active_users_24h"].tolist())

if billing.empty:
    billing_dates = []
    billing_edx = []
    billing_otter = []
else:
    billing_dates = sorted(billing["date"].dt.strftime("%Y-%m-%d").unique().tolist())
    billing_edx = (
        billing[billing["service"] == "edx"]
        .set_index(billing[billing["service"] == "edx"]["date"].dt.strftime("%Y-%m-%d"))["cost"]
        .reindex(billing_dates, fill_value=0)
        .tolist()
    )
    billing_otter = (
        billing[billing["service"] == "otter-service"]
        .set_index(billing[billing["service"] == "otter-service"]["date"].dt.strftime("%Y-%m-%d"))["cost"]
        .reindex(billing_dates, fill_value=0)
        .tolist()
    )
billing_dates_json = json.dumps(billing_dates)
billing_edx_json = json.dumps(billing_edx)
billing_otter_json = json.dumps(billing_otter)

updated = date.today().isoformat()

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>88x JupyterHub Activity</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: system-ui, sans-serif; background: #f5f5f5; color: #222; padding: 2rem; }}
    h1 {{ font-size: 1.6rem; margin-bottom: 0.25rem; }}
    .updated {{ color: #888; font-size: 0.85rem; margin-bottom: 2rem; }}
    .card {{ background: #fff; border-radius: 8px; padding: 1.5rem; margin-bottom: 2rem; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }}
    h2 {{ font-size: 1.1rem; margin-bottom: 1rem; }}
    canvas {{ max-height: 320px; }}
    input {{ width: 100%; padding: 0.5rem 0.75rem; border: 1px solid #ddd; border-radius: 6px; font-size: 0.9rem; margin-bottom: 1rem; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
    th {{ text-align: left; padding: 0.5rem 0.75rem; border-bottom: 2px solid #eee; color: #555; }}
    td {{ padding: 0.45rem 0.75rem; border-bottom: 1px solid #f0f0f0; }}
    tr:hover td {{ background: #fafafa; }}
    .none {{ color: #bbb; }}
  </style>
</head>
<body>
  <h1>88x JupyterHub Activity</h1>
  <p class="updated">Last updated: {updated}</p>

  <div class="card">
    <h2>Monthly Active Users by Course</h2>
    <canvas id="chart"></canvas>
  </div>

  <div class="card">
    <h2>Historical Monthly Active Users (hub-wide, 30-day window)</h2>
    <canvas id="historical-chart"></canvas>
  </div>

  <div class="card">
    <h2>Daily Infrastructure Cost (USD)</h2>
    <canvas id="billing-chart"></canvas>
  </div>

  <div class="card">
    <h2>Per-Student Last Activity</h2>
    <input type="text" id="search" placeholder="Search by User ID..." />
    <table>
      <thead>
        <tr>
          <th>User ID</th>
          <th>88.1 Last Activity</th>
          <th>88.2 Last Activity</th>
          <th>88.3 Last Activity</th>
        </tr>
      </thead>
      <tbody id="table-body"></tbody>
    </table>
  </div>

  <script>
    const monthly = {monthly_json};
    const activity = {activity_json};

    // --- Chart ---
    const labels = monthly.map(r => r["month-year"]);
    new Chart(document.getElementById("chart"), {{
      type: "bar",
      data: {{
        labels,
        datasets: [
          {{ label: "88.1", data: monthly.map(r => r["88.1 users"]), backgroundColor: "#4e79a7" }},
          {{ label: "88.2", data: monthly.map(r => r["88.2 users"]), backgroundColor: "#f28e2b" }},
          {{ label: "88.3", data: monthly.map(r => r["88.3 users"]), backgroundColor: "#59a14f" }},
        ]
      }},
      options: {{
        responsive: true,
        plugins: {{ legend: {{ position: "top" }} }},
        scales: {{ x: {{ stacked: false }}, y: {{ beginAtZero: true, ticks: {{ precision: 0 }} }} }}
      }}
    }});

    // --- Historical active users chart ---
    const historicalMonths = {historical_months_json};
    const historical30d = {historical_30d_json};
    const historical24h = {historical_24h_json};
    new Chart(document.getElementById("historical-chart"), {{
      type: "line",
      data: {{
        labels: historicalMonths,
        datasets: [
          {{
            label: "30-day active users",
            data: historical30d,
            borderColor: "#4e79a7",
            backgroundColor: "rgba(78,121,167,0.15)",
            fill: true,
            tension: 0.3,
            pointRadius: 3,
          }},
          {{
            label: "24-hour active users",
            data: historical24h,
            borderColor: "#f28e2b",
            backgroundColor: "rgba(242,142,43,0.1)",
            fill: false,
            tension: 0.3,
            pointRadius: 3,
          }},
        ]
      }},
      options: {{
        responsive: true,
        plugins: {{ legend: {{ position: "top" }} }},
        scales: {{ y: {{ beginAtZero: true, ticks: {{ precision: 0 }} }} }}
      }}
    }});

    // --- Billing chart ---
    const billingDates = {billing_dates_json};
    const billingEdx = {billing_edx_json};
    const billingOtter = {billing_otter_json};
    new Chart(document.getElementById("billing-chart"), {{
      type: "bar",
      data: {{
        labels: billingDates,
        datasets: [
          {{ label: "edx", data: billingEdx, backgroundColor: "#4e79a7", stack: "cost" }},
          {{ label: "otter-service", data: billingOtter, backgroundColor: "#e15759", stack: "cost" }},
        ]
      }},
      options: {{
        responsive: true,
        plugins: {{ legend: {{ position: "top" }} }},
        scales: {{
          x: {{ stacked: true }},
          y: {{ stacked: true, beginAtZero: true, ticks: {{ callback: v => "$" + v.toFixed(0) }} }}
        }}
      }}
    }});

    // --- Table ---
    const tbody = document.getElementById("table-body");

    function renderTable(rows) {{
      tbody.innerHTML = rows.map(r => `
        <tr>
          <td>${{r["User ID"]}}</td>
          <td class="${{r["88.1 last activity"] === "none" ? "none" : ""}}">${{r["88.1 last activity"]}}</td>
          <td class="${{r["88.2 last activity"] === "none" ? "none" : ""}}">${{r["88.2 last activity"]}}</td>
          <td class="${{r["88.3 last activity"] === "none" ? "none" : ""}}">${{r["88.3 last activity"]}}</td>
        </tr>`).join("");
    }}

    renderTable(activity);

    document.getElementById("search").addEventListener("input", e => {{
      const q = e.target.value.toLowerCase();
      renderTable(activity.filter(r => String(r["User ID"]).toLowerCase().includes(q)));
    }});
  </script>
</body>
</html>
"""

DASHBOARD_DIR.mkdir(exist_ok=True)
(DASHBOARD_DIR / "index.html").write_text(html, encoding="utf-8")
print(f"Dashboard written to {DASHBOARD_DIR / 'index.html'}")
