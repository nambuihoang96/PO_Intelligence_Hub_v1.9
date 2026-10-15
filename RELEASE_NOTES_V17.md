# PO Intelligence Hub v1.7 — Unified Research Studio (MVP)

**Goal:** Merge the v1.5 project/research/action workspace with optional Sensor Tower CSV analysis; work for Games/Puzzle and Utilities. This is a functional MVP, not a completed market research report or a claim that any app is currently scaling.

## Included

- Main Hub v1.5.1 unchanged in its core routes/workflows, with a new **Research Studio v1.7** sidebar link.
- **Research Projects**: create a project from a natural-language question with editable market, GEO, and public discovery keywords. Projects use the existing v1.5 SQLite `projects` table.
- **Public-first**: invoke existing v1.5 guided Apple/Android store discovery (Android requires the optional connector), save real store listing candidates with original links, and collect keyword-relevant RSS context where configured. Public-only research does not require CSV.
- **CSV optional**: upload actual UTF-16 TSV / UTF-8 CSV Sensor Tower exports into the same SQLite database. SHA-256 duplicate protection, 120-row batches, source filename and row provenance. No bundled user data. PoP/YoY merge by Unified ID + platform + GEO + exact period.
- **Market Overview**: actual dataset coverage, scope/period, deterministic Top PoP absolute growth and new-release candidates. A broad category match is NOT verified Puzzle/Utilities subgenre classification. Mismatched Games-only CSV does not silently generate Utilities metrics.
- **Data Explorer**: search, column-header filters, sort, Top 10/20/50/100/All, export current view, metric-specific evidence inspector, and verified-period-only snapshot timeline (not invented daily downloads).
- **Public signals**: dated store snapshots for future review-count comparisons, and RSS article evidence. Neither proves downloads or UA scale.
- **Real AI integration**: evidence-scoped packet for ChatGPT Manual or opt-in Codex CLI Auto, structured JSON import with evidence-ID reference validation. No hard-coded AI market findings.
- **Market-level insights**: executive summary, market findings, subcategory assessments, rising apps, research gaps and research-action drafts. Explicit PO click can send a validated research-action draft to the **v1.5 Action Registry**. No automatic Product Experiment.
- **Reports**: HTML report, print-to-PDF, CSV export of filtered view, source appendix and methodological limitations.

## Limitations (important)

- **Not a complete trend detector:** Public Store Search is discovery, not app ranking or verified downloads. With one CSV snapshot, PoP is a supplied comparison but there is no daily/weekly timeline. Review-count changes need repeated collections.
- **Not verified subgenre taxonomy:** AI may propose classification with evidence, but the app has no gameplay/feature verification workflow yet.
- **Not full semantic fact-checking:** AI JSON validation checks evidence IDs against the exact packet and shape; it cannot automatically prove every natural-language claim is factually entailed. PO review remains necessary.
- **No verified cross-platform app identity mapping:** Do not combine iOS/Android/Unified or GEOs without explicit matching and comparable scopes.
- **No profitable-UA inference:** Public and Sensor Tower data alone do not establish CPI, spend, retention, ad revenue or ROAS.
- **No automatic action approval:** Studio AI suggestions require explicit PO click; Opportunity and Experiment workflow remains in v1.5.
- **Not live-tested on Windows:** Backend tests and a Chromium UI simulation passed in this environment; run on a Windows machine to validate browser/CLI setup.

## Run

1. Extract the ZIP to a new folder (do not overwrite an existing live SQLite database without a backup).
2. Run `RUN_WINDOWS.bat` with Python 3.10+ installed.
3. In the main Hub sidebar, click **Research Studio v1.7**, or visit `http://127.0.0.1:8765/studio.html`.
4. Create a Research Project with a question, review GEO and keywords.
5. For public-only: click **Collect public data**; revisit **Sources & Import** to check progress/errors, then **Prepare AI Market Analysis**.
6. For hybrid: also import one or more actual Sensor Tower CSV exports. The files are stored in SQLite as normalized evidence, not bundled with the app.
7. For AI: use **Copy for ChatGPT Manual** (paste the packet and request strictly formatted JSON), then **Validate & Import AI Analysis**, or enable Codex in the main Hub Settings and explicitly confirm **Run Codex Auto**.
8. Open **Linked Report** to export HTML or print/save PDF; filter Data Explorer for CSV export.

**Privacy:** The server listens on localhost. Imported CSV data is stored in `data/research.sqlite3` on your computer. Manual AI mode requires deliberately copying a selected evidence packet into ChatGPT; Codex Auto also receives the packet. Do not use AI with confidential exports without permission.
