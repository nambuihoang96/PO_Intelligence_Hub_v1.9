# PO Intelligence Hub v1.6.1 — CSV Import & Evidence Lab (Windows)

## Quick start

1. Install Python 3.10+ (no paid API or Python package install needed for the CSV Lab).
2. Double-click `RUN_WINDOWS.bat`.
3. Open `http://127.0.0.1:8765/v16-demo.html` or click **v1.6.1 CSV Lab** in the Hub sidebar.
4. Go to **Import & Sources** and select one or more Sensor Tower CSV files. The Lab starts EMPTY; **no user CSV or app records are bundled**.
5. The importer supports Sensor Tower's UTF-16LE/tab-delimited CSV and ordinary UTF-8 comma-delimited CSV, provided columns include `Unified Name`, `Unified ID`, `Downloads (Absolute)`, and either `Downloads (PoP Growth)` or `Downloads (YoY Growth)`.
6. Open **Data Explorer**. Filter directly inside the table's second header row (game, publisher, category, platform, GEO, release range, downloads, PoP/YoY, revenue, DAU, source file); click column titles to sort; choose Top 10/20/50/100 or All.
7. Click **Trace →** to inspect CSV filename, row number, scope, raw metrics, finding and rule-based interpretation.
8. **Growth Intelligence** shows bars from the current filtered/sorted Top N (up to 100 bars).
9. **Report Builder** uses the same filtered/sorted Top N to create a table, chart and evidence-backed findings. Export the selected rows as CSV, download a self-contained HTML report, or print the report to PDF via the browser.

## Important behavior

- Imported data is parsed in your local browser session. Files are NOT uploaded to the server and are NOT bundled with the distribution. **Reloading the page requires re-import** (demo limitation).
- You may import PoP and YoY exports together. Records merge only when `Unified ID`, platform, GEO and period match; they are not double-counted. A different period, GEO or platform is kept as a separate record.
- The export period and GEO are extracted from the standard Sensor Tower filename. If missing, the importer keeps the scope `Unknown` rather than guessing.
- The importer validates columns and shows errors instead of fabricating unavailable metrics. Empty growth % remains N/A (not zero). Source percentages are stored as fractions (e.g. `0.1` = `10%`); UI and exported `*_pct` columns display percentages.
- Sorting, header filters, Top N, chart, report and CSV export all use the same filtered dataset. CSV exports every selected Top N row; HTML/print reports show up to 1,000 rows for usability.
- A report includes original filename and CSV row number for each game. Findings are deterministic and rule-based, NOT AI-generated. PO review marks are temporary and do not create actions in the Hub SQLite database.
- Worldwide Unified Sensor Tower estimates are not per-platform/per-GEO data. No inferred UA spend, ROAS, verified Puzzle subgenre, or download history is generated.

## Tests

- Existing Hub Python backend tests: 42/42 passed.
- `node tests/test_v16_core.cjs <downloads_file.csv> <yoy_file.csv>`: real CSV parser, merge, source lineage, sort and numeric filters passed on two user-provided test files (20,000 rows; 13,852 distinct records).
- Headless Chromium smoke test: import empty-state, upload, table-header filters, Top N, Trace, CSV/HTML download, chart and clear all passed.

This is a functional local demo, not a completed production integration of imported CSV with the Hub's public-source Research Project/AI/Action database.
