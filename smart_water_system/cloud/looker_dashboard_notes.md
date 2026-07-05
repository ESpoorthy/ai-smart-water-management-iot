# Looker Studio Dashboard — Setup Notes

Wire the BigQuery export into a live Looker Studio dashboard for
screenshots and judge slides.  Estimated setup time: 20 minutes.

---

## Prerequisites

| Item | Status |
|---|---|
| BigQuery export completed | Run `python cloud/export_to_bigquery.py` |
| GCP project with BigQuery API enabled | Required |
| Google account with access to the BQ project | Required |
| Looker Studio account (free) | [datastudio.google.com](https://datastudio.google.com) |

---

## Step 1 — Verify the BigQuery table

1. Open [BigQuery Console](https://console.cloud.google.com/bigquery).
2. Navigate to **`your-project` → `smart_water` → `sensor_data`**.
3. Click **Preview** — confirm rows are present with columns:
   `id`, `timestamp`, `flow`, `pressure`, `ph`, `turbidity`,
   `temperature`, `exported_at`.
4. Run a quick sanity query:
   ```sql
   SELECT
     MIN(timestamp) AS earliest,
     MAX(timestamp) AS latest,
     COUNT(*)       AS total_rows,
     ROUND(AVG(flow), 2)      AS avg_flow,
     ROUND(AVG(turbidity), 2) AS avg_turbidity
   FROM `your-project.smart_water.sensor_data`
   ```

---

## Step 2 — Create a new Looker Studio report

1. Go to [Looker Studio](https://lookerstudio.google.com) → **Blank Report**.
2. When prompted to add a data source, choose **BigQuery**.
3. Authenticate → select your GCP project → dataset `smart_water`
   → table `sensor_data` → click **Add**.
4. Looker Studio will import the schema automatically.

---

## Step 3 — Set up calculated fields

Add these in **Resource → Manage added data sources → Edit → Add Field**:

| Field name | Formula | Notes |
|---|---|---|
| `is_anomaly_flow` | `CASE WHEN flow < 8 THEN "Low" WHEN flow > 22 THEN "High" ELSE "Normal" END` | Flow status |
| `is_anomaly_ph` | `CASE WHEN ph < 6.5 OR ph > 8.5 THEN "Out of Range" ELSE "Normal" END` | pH status |
| `is_anomaly_turbidity` | `CASE WHEN turbidity > 5 THEN "High" ELSE "Normal" END` | Turbidity flag |
| `hour_of_day` | `HOUR(timestamp)` | For daily-pattern charts |
| `date_only` | `TODATE(timestamp, "YYYY-MM-DD")` | For daily aggregations |

---

## Step 4 — Recommended charts

### Chart 1 — Real-Time KPI Scorecards (top row)
- **Type:** Scorecard
- **Metrics:** `AVG(flow)`, `AVG(pressure)`, `AVG(ph)`, `AVG(turbidity)`
- **Comparison period:** Previous period
- Add conditional colouring: green if within safe range, red otherwise.

### Chart 2 — Flow & Pressure Over Time
- **Type:** Time Series
- **Dimension:** `timestamp`  (granularity: Minute or Hour)
- **Metrics:** `flow`, `pressure`
- **Style:** Dual Y-axis, flow on left, pressure on right.

### Chart 3 — Anomaly Heatmap
- **Type:** Pivot Table or Heatmap
- **Rows:** `date_only`
- **Columns:** `hour_of_day`
- **Metric:** `COUNT(id)` filtered where `is_anomaly_flow ≠ "Normal"`
- Shows which hours of which days have the most anomalies.

### Chart 4 — Water Quality Trend
- **Type:** Combo Chart (Line + Bar)
- **Dimension:** `timestamp`
- **Bar metric:** `turbidity`
- **Line metric:** `ph`
- Add reference bands: pH 6.5–8.5, turbidity < 5 NTU.

### Chart 5 — Flow Distribution
- **Type:** Bar Chart
- **Dimension:** `is_anomaly_flow`
- **Metric:** `COUNT(id)`
- Quick view of Normal vs Low vs High flow proportion.

### Chart 6 — Daily Summary Table
- **Type:** Table with heatmap
- **Dimension:** `date_only`
- **Metrics:** `AVG(flow)`, `AVG(pressure)`, `AVG(ph)`,
  `AVG(turbidity)`, `COUNT(id)`
- Heatmap on turbidity column.

---

## Step 5 — Filters and date controls

1. Add a **Date Range Control** (drag from toolbar) — set default to
   "Last 7 days".
2. Add a **Data Control** so viewers can switch between tables if you
   export multiple zones later.
3. Optional: add a **Drop-Down List** filter on `is_anomaly_flow` so
   judges can isolate anomalous periods instantly.

---

## Step 6 — Sharing for the demo

1. **File → Share → Manage access** → set to "Anyone with the link can view".
2. Copy the shareable link for your slide deck.
3. For a live demo, use **View** mode (not Edit) — it auto-refreshes if
   you set the report's data freshness to "Every 15 minutes" under
   **Resource → Report settings**.

> **Tip for judges:** Schedule the BigQuery export as a cron job
> (`0 * * * * python cloud/export_to_bigquery.py --mode=incremental`)
> and the Looker dashboard will update every hour automatically.

---

## Step 7 — Keep BQ fresh during the live demo

Run incremental export in the background before the presentation:

```bash
# Windows — run in a separate terminal
python cloud/export_to_bigquery.py --mode=incremental
```

Or add to `run_system.sh` (existing script — one line at the end):
```bash
python cloud/export_to_bigquery.py --mode=incremental &
```

---

## Recommended dashboard layout (for slides)

```
┌─────────────────────────────────────────────────────────┐
│  💧 Smart Water Management — Live Analytics             │
│  [Date range control]          [Last refreshed: HH:MM]  │
├──────────┬──────────┬──────────┬──────────┬────────────┤
│ Avg Flow │ Avg Pres │  Avg pH  │ Avg Turb │ Total Rdgs │  ← Scorecards
├──────────┴──────────┴──────────┴──────────┴────────────┤
│           Flow & Pressure Time Series                   │  ← Chart 2
├─────────────────────────┬───────────────────────────────┤
│  Water Quality Trend    │   Anomaly Distribution        │  ← Charts 4 & 5
├─────────────────────────┴───────────────────────────────┤
│                Daily Summary Table                      │  ← Chart 6
└─────────────────────────────────────────────────────────┘
```

---

## Troubleshooting

| Issue | Fix |
|---|---|
| "No data" in charts | Check BQ preview — re-run export if empty |
| Timestamp shows wrong timezone | Add `DATETIME_DIFF` or use `TODATE` with UTC offset in calculated field |
| Permission denied on BQ | Ensure the Google account has `BigQuery Data Viewer` role on the project |
| Scorecard shows 0 | Check the date range control — default may exclude your data window |
