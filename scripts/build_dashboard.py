import json
import pandas as pd
from pathlib import Path
from datetime import date, timedelta

BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output"
DATA_DIR = BASE_DIR / "data"
DASHBOARD_DIR = BASE_DIR / "docs"

SECTIONS = ["88E.1", "88E.2", "88E.3", "88B.1", "88B.2", "88B.3", "88C.1", "88C.2", "88C.3"]
COURSES = {"88E": ["88E.1", "88E.2", "88E.3"], "88B": ["88B.1", "88B.2", "88B.3"], "88C": ["88C.1", "88C.2", "88C.3"]}
SECTION_COLORS = {
    "88E.1": "#1a5c9c", "88E.2": "#4e79a7", "88E.3": "#89b8d9",
    "88B.1": "#1e7c1a", "88B.2": "#59a14f", "88B.3": "#97cb93",
    "88C.1": "#c06a00", "88C.2": "#f28e2b", "88C.3": "#f5bc75",
}
BILLING_PALETTE = ["#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f",
                   "#edc948", "#b07aa1", "#ff9da7", "#9c755f", "#bab0ac"]

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
monthly = pd.read_csv(DATA_DIR / "monthly_activity.csv")
for s in SECTIONS:
    if f"{s} users" not in monthly.columns:
        monthly[f"{s} users"] = 0

activity = pd.read_csv(OUTPUT_DIR / "user_activity.csv")
for s in SECTIONS:
    col = f"{s} last activity"
    if col not in activity.columns:
        activity[col] = "none"

billing = pd.read_csv(OUTPUT_DIR / "billing.csv", parse_dates=["date"])
historical = pd.read_csv(DATA_DIR / "hub_historical_users.csv")

snapshot_path = DATA_DIR / "daily_snapshots.csv"
snapshots = pd.read_csv(snapshot_path) if snapshot_path.exists() else pd.DataFrame()

# ---------------------------------------------------------------------------
# Monthly chart JSON
# ---------------------------------------------------------------------------
monthly_records = monthly.to_dict(orient="records")
monthly_json = json.dumps(monthly_records)
section_colors_json = json.dumps(SECTION_COLORS)
courses_json = json.dumps(COURSES)

# ---------------------------------------------------------------------------
# Activity table JSON
# ---------------------------------------------------------------------------
activity_json = json.dumps(activity.fillna("none").to_dict(orient="records"))

# ---------------------------------------------------------------------------
# Historical chart JSON
# ---------------------------------------------------------------------------
historical_months_json = json.dumps(historical["month"].tolist())
historical_30d_json = json.dumps(historical["active_users_30d"].tolist())
historical_24h_json = json.dumps(historical["active_users_24h"].tolist())

# ---------------------------------------------------------------------------
# Daily snapshot: 30-day chart + yesterday summary
# ---------------------------------------------------------------------------
today_str = date.today().isoformat()
cutoff_30d = (date.today() - timedelta(days=30)).isoformat()

if not snapshots.empty and "date" in snapshots.columns:
    recent = snapshots[snapshots["date"] >= cutoff_30d].copy()
    active_cols = [f"{s} active" for s in SECTIONS if f"{s} active" in recent.columns]
    recent["total_active"] = recent[active_cols].sum(axis=1) if active_cols else 0
    daily_dates = recent["date"].tolist()
    daily_active = recent["total_active"].tolist()
    daily_running = recent["running_servers"].fillna(0).tolist() if "running_servers" in recent.columns else [0] * len(daily_dates)

    prev = snapshots[snapshots["date"] < today_str]
    if not prev.empty:
        latest = prev.iloc[-1]
        summary_date = str(latest["date"])
        summary_running = int(latest["running_servers"]) if pd.notna(latest.get("running_servers")) else 0
        summary_sections = {
            s: int(latest[f"{s} active"]) if f"{s} active" in latest.index and pd.notna(latest[f"{s} active"]) else 0
            for s in SECTIONS
        }
    else:
        summary_date = None
        summary_running = 0
        summary_sections = {s: 0 for s in SECTIONS}
else:
    daily_dates = []
    daily_active = []
    daily_running = []
    summary_date = None
    summary_running = 0
    summary_sections = {s: 0 for s in SECTIONS}

daily_dates_json = json.dumps(daily_dates)
daily_active_json = json.dumps(daily_active)
daily_running_json = json.dumps(daily_running)
summary_json = json.dumps({"date": summary_date, "running_servers": summary_running, "sections": summary_sections})

# ---------------------------------------------------------------------------
# Billing chart JSON — dynamic service breakdown
# ---------------------------------------------------------------------------
if billing.empty:
    billing_dates = []
    billing_services = {}
else:
    billing_dates = sorted(billing["date"].dt.strftime("%Y-%m-%d").unique().tolist())
    billing_services = {}
    for svc in sorted(billing["service"].dropna().unique()):
        svc_mask = billing["service"] == svc
        svc_series = (
            billing[svc_mask]
            .set_index(billing.loc[svc_mask, "date"].dt.strftime("%Y-%m-%d"))["cost"]
            .reindex(billing_dates, fill_value=0)
        )
        billing_services[svc] = svc_series.tolist()

billing_dates_json = json.dumps(billing_dates)
billing_services_json = json.dumps(billing_services)
billing_palette_json = json.dumps(BILLING_PALETTE)

updated = date.today().isoformat()

# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------
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
    .no-data {{ color: #aaa; font-size: 0.9rem; padding: 1rem 0; }}
    /* Summary stats */
    .stat-row {{ display: flex; gap: 1rem; margin-bottom: 1.25rem; flex-wrap: wrap; }}
    .stat-box {{ background: #f8f8f8; border-radius: 6px; padding: 0.75rem 1.25rem; text-align: center; min-width: 140px; }}
    .stat-value {{ display: block; font-size: 1.8rem; font-weight: 600; color: #333; }}
    .stat-label {{ display: block; font-size: 0.78rem; color: #777; margin-top: 0.15rem; }}
    /* Filter buttons */
    .filter-row {{ display: flex; gap: 0.5rem; margin-bottom: 0.75rem; flex-wrap: wrap; align-items: center; }}
    .filter-btn {{ padding: 0.3rem 0.85rem; border: 1px solid #ccc; border-radius: 20px; background: #fff;
                   font-size: 0.85rem; cursor: pointer; color: #555; transition: all 0.15s; }}
    .filter-btn:hover {{ border-color: #4e79a7; color: #4e79a7; }}
    .filter-btn.active {{ background: #4e79a7; border-color: #4e79a7; color: #fff; }}
    /* Table */
    input[type=text] {{ width: 100%; padding: 0.5rem 0.75rem; border: 1px solid #ddd; border-radius: 6px;
                        font-size: 0.9rem; margin-bottom: 1rem; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
    th {{ text-align: left; padding: 0.5rem 0.75rem; border-bottom: 2px solid #eee; color: #555; white-space: nowrap; }}
    th.sortable {{ cursor: pointer; user-select: none; }}
    th.sortable:hover {{ color: #4e79a7; }}
    td {{ padding: 0.45rem 0.75rem; border-bottom: 1px solid #f0f0f0; }}
    tr:hover td {{ background: #fafafa; }}
    .none {{ color: #bbb; }}
    .sort-arrow {{ font-size: 0.7rem; margin-left: 3px; }}
  </style>
</head>
<body>
  <h1>88x JupyterHub Activity</h1>
  <p class="updated">Last updated: {updated}</p>

  <!-- 1. Monthly Active Users -->
  <div class="card">
    <h2>Monthly Active Users by Course</h2>
    <canvas id="chart"></canvas>
  </div>

  <!-- 2. Yesterday's Summary -->
  <div class="card">
    <h2>Yesterday's Activity Summary</h2>
    <div id="summary-container">
      <p class="no-data" id="summary-no-data" style="display:none">No snapshot data yet — will appear after the next pipeline run.</p>
      <div id="summary-content" style="display:none">
        <div class="stat-row">
          <div class="stat-box">
            <span class="stat-value" id="stat-running">--</span>
            <span class="stat-label">Est. Peak Concurrent Servers</span>
          </div>
          <div class="stat-box">
            <span class="stat-value" id="stat-total">--</span>
            <span class="stat-label">Total Active Users</span>
          </div>
        </div>
        <p style="font-size:0.8rem;color:#888;margin-bottom:0.75rem" id="summary-date-label"></p>
        <table>
          <thead>
            <tr><th>Course</th><th>Section</th><th>Active Users</th></tr>
          </thead>
          <tbody id="summary-body"></tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- 3. 30-day Daily Users + Concurrent chart -->
  <div class="card">
    <h2>Last 30 Days: Daily Active Users &amp; Peak Concurrent Servers</h2>
    <div id="daily-no-data" class="no-data" style="display:none">No snapshot data yet — will appear after the next pipeline run.</div>
    <canvas id="daily-chart"></canvas>
  </div>

  <!-- 4. Historical Monthly Active Users -->
  <div class="card">
    <h2>Historical Monthly Active Users (hub-wide, 30-day window)</h2>
    <canvas id="historical-chart"></canvas>
  </div>

  <!-- 5. Billing -->
  <div class="card">
    <h2>Daily Infrastructure Cost (USD)</h2>
    <canvas id="billing-chart"></canvas>
  </div>

  <!-- 6. Per-Student Table -->
  <div class="card">
    <h2>Per-Student Last Activity</h2>
    <div class="filter-row">
      <span style="font-size:0.85rem;color:#777;margin-right:0.25rem">Show:</span>
      <button class="filter-btn active" data-course="All">All</button>
      <button class="filter-btn" data-course="88E">88E</button>
      <button class="filter-btn" data-course="88B">88B</button>
      <button class="filter-btn" data-course="88C">88C</button>
    </div>
    <input type="text" id="search" placeholder="Search by User ID..." />
    <table>
      <thead>
        <tr id="table-header-row"></tr>
      </thead>
      <tbody id="table-body"></tbody>
    </table>
  </div>

  <script>
    const SECTION_COLORS = {section_colors_json};
    const COURSES = {courses_json};
    const ALL_SECTIONS = {json.dumps(SECTIONS)};
    const monthly = {monthly_json};
    const activity = {activity_json};
    const summary = {summary_json};
    const historicalMonths = {historical_months_json};
    const historical30d = {historical_30d_json};
    const historical24h = {historical_24h_json};
    const dailyDates = {daily_dates_json};
    const dailyActive = {daily_active_json};
    const dailyRunning = {daily_running_json};
    const billingDates = {billing_dates_json};
    const billingServices = {billing_services_json};
    const BILLING_PALETTE = {billing_palette_json};

    // -----------------------------------------------------------------------
    // 1. Monthly Active Users — stacked by section, grouped by course
    // -----------------------------------------------------------------------
    const monthlyLabels = monthly.map(r => r["month-year"]);
    const monthlyDatasets = [];
    for (const [course, sections] of Object.entries(COURSES)) {{
      for (const section of sections) {{
        monthlyDatasets.push({{
          label: section,
          data: monthly.map(r => Number(r[section + " users"] || 0)),
          backgroundColor: SECTION_COLORS[section],
          stack: course,
        }});
      }}
    }}
    new Chart(document.getElementById("chart"), {{
      type: "bar",
      data: {{ labels: monthlyLabels, datasets: monthlyDatasets }},
      options: {{
        responsive: true,
        plugins: {{ legend: {{ position: "top" }} }},
        scales: {{
          x: {{ stacked: true }},
          y: {{ stacked: true, beginAtZero: true, ticks: {{ precision: 0 }} }}
        }}
      }}
    }});

    // -----------------------------------------------------------------------
    // 2. Yesterday's Summary
    // -----------------------------------------------------------------------
    if (summary.date) {{
      document.getElementById("summary-no-data").style.display = "none";
      document.getElementById("summary-content").style.display = "";
      document.getElementById("stat-running").textContent = summary.running_servers;
      const totalActive = Object.values(summary.sections).reduce((a, b) => a + b, 0);
      document.getElementById("stat-total").textContent = totalActive;
      document.getElementById("summary-date-label").textContent = "Data from " + summary.date;
      const tbody = document.getElementById("summary-body");
      const rows = [];
      for (const [course, sections] of Object.entries(COURSES)) {{
        for (const section of sections) {{
          rows.push(`<tr><td>${{course}}</td><td>${{section}}</td><td>${{summary.sections[section] || 0}}</td></tr>`);
        }}
      }}
      tbody.innerHTML = rows.join("");
    }} else {{
      document.getElementById("summary-no-data").style.display = "";
      document.getElementById("summary-content").style.display = "none";
    }}

    // -----------------------------------------------------------------------
    // 3. 30-day Daily Users + Concurrent chart
    // -----------------------------------------------------------------------
    if (dailyDates.length === 0) {{
      document.getElementById("daily-no-data").style.display = "";
      document.getElementById("daily-chart").style.display = "none";
    }} else {{
      new Chart(document.getElementById("daily-chart"), {{
        type: "line",
        data: {{
          labels: dailyDates,
          datasets: [
            {{
              label: "Daily Active Users",
              data: dailyActive,
              borderColor: "#4e79a7",
              backgroundColor: "rgba(78,121,167,0.12)",
              fill: true,
              tension: 0.3,
              pointRadius: 3,
            }},
            {{
              label: "Peak Concurrent Servers",
              data: dailyRunning,
              borderColor: "#e15759",
              backgroundColor: "rgba(225,87,89,0.05)",
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
    }}

    // -----------------------------------------------------------------------
    // 4. Historical Monthly Active Users
    // -----------------------------------------------------------------------
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

    // -----------------------------------------------------------------------
    // 5. Billing — dynamic per-service stacked bars
    // -----------------------------------------------------------------------
    const billingDatasets = Object.entries(billingServices).map(([svc, data], i) => ({{
      label: svc,
      data,
      backgroundColor: BILLING_PALETTE[i % BILLING_PALETTE.length],
      stack: "cost",
    }}));
    new Chart(document.getElementById("billing-chart"), {{
      type: "bar",
      data: {{ labels: billingDates, datasets: billingDatasets }},
      options: {{
        responsive: true,
        plugins: {{ legend: {{ position: "top" }} }},
        scales: {{
          x: {{ stacked: true }},
          y: {{ stacked: true, beginAtZero: true, ticks: {{ callback: v => "$" + v.toFixed(2) }} }}
        }}
      }}
    }});

    // -----------------------------------------------------------------------
    // 6. Per-Student Table — filterable by course, sortable columns
    // -----------------------------------------------------------------------
    const COURSE_SECTIONS = COURSES;
    let currentFilter = "All";
    let sortCol = "User ID";
    let sortAsc = true;
    let searchQuery = "";

    function getVisibleSections() {{
      return currentFilter === "All" ? ALL_SECTIONS : COURSE_SECTIONS[currentFilter];
    }}

    function getCellValue(row, col) {{
      if (col === "User ID") return String(row["User ID"] ?? "");
      return row[col + " last activity"] ?? "none";
    }}

    function getFilteredRows() {{
      let rows = activity;
      if (searchQuery) {{
        rows = rows.filter(r => String(r["User ID"]).toLowerCase().includes(searchQuery));
      }}
      if (currentFilter !== "All") {{
        const secs = COURSE_SECTIONS[currentFilter];
        rows = rows.filter(r => secs.some(s => r[s + " last activity"] !== "none"));
      }}
      return rows;
    }}

    function sortedRows(rows) {{
      return [...rows].sort((a, b) => {{
        const va = getCellValue(a, sortCol);
        const vb = getCellValue(b, sortCol);
        if (sortCol !== "User ID") {{
          if (va === "none" && vb === "none") return 0;
          if (va === "none") return 1;
          if (vb === "none") return -1;
        }}
        const cmp = va < vb ? -1 : va > vb ? 1 : 0;
        return sortAsc ? cmp : -cmp;
      }});
    }}

    function renderTable() {{
      const sections = getVisibleSections();
      const rows = sortedRows(getFilteredRows());

      // Rebuild header
      const headerRow = document.getElementById("table-header-row");
      const makeArrow = col => sortCol === col ? `<span class="sort-arrow">${{sortAsc ? "↑" : "↓"}}</span>` : "";
      let headerHTML = `<th class="sortable" data-col="User ID">User ID${{makeArrow("User ID")}}</th>`;
      for (const s of sections) {{
        headerHTML += `<th class="sortable" data-col="${{s}}">${{s}}${{makeArrow(s)}}</th>`;
      }}
      headerRow.innerHTML = headerHTML;

      const tbody = document.getElementById("table-body");
      tbody.innerHTML = rows.map(r => {{
        const cells = sections.map(s => {{
          const val = r[s + " last activity"] ?? "none";
          return `<td class="${{val === "none" ? "none" : ""}}">${{val}}</td>`;
        }}).join("");
        return `<tr><td>${{r["User ID"]}}</td>${{cells}}</tr>`;
      }}).join("");
    }}

    document.getElementById("table-header-row").addEventListener("click", e => {{
      const th = e.target.closest("th.sortable");
      if (!th) return;
      const col = th.dataset.col;
      if (sortCol === col) {{
        sortAsc = !sortAsc;
      }} else {{
        sortCol = col;
        sortAsc = true;
      }}
      renderTable();
    }});

    document.querySelectorAll(".filter-btn").forEach(btn => {{
      btn.addEventListener("click", () => {{
        currentFilter = btn.dataset.course;
        sortCol = "User ID";
        sortAsc = true;
        document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        renderTable();
      }});
    }});

    document.getElementById("search").addEventListener("input", e => {{
      searchQuery = e.target.value.toLowerCase();
      renderTable();
    }});

    renderTable();
  </script>
</body>
</html>
"""

DASHBOARD_DIR.mkdir(exist_ok=True)
(DASHBOARD_DIR / "index.html").write_text(html, encoding="utf-8")
print(f"Dashboard written to {DASHBOARD_DIR / 'index.html'}")
