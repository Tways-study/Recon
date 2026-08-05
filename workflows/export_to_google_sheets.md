# Workflow: Export to Google Sheets

## Objective
Write all competitor research data from `.tmp/` to a Google Sheet with a Master comparison tab and one tab per competitor.

## One-Time Setup

### 1. Create a Google Cloud project
- Go to https://console.cloud.google.com
- Create a new project (e.g. "Competitor Research")

### 2. Enable APIs
- APIs & Services → Library
- Enable: **Google Sheets API** and **Google Drive API**

### 3. Create OAuth credentials
- APIs & Services → Credentials → Create Credentials → OAuth client ID
- Application type: **Desktop app**
- Download the JSON → save as `credentials.json` in the project root

### 4. First run — browser auth
```bash
python tools/export_to_sheets.py
```
A browser window opens for Google authorization. After approving, `token.json` is written automatically. All subsequent runs use `token.json` silently.

## Runtime

```bash
# Use an existing sheet (recommended — preserves the URL)
python tools/export_to_sheets.py --sheet-id "YOUR_SHEET_ID"

# Auto-create a new sheet
python tools/export_to_sheets.py
```

The Sheet ID is in the Google Sheets URL:
`https://docs.google.com/spreadsheets/d/`**`SHEET_ID_HERE`**`/edit`

## Sheet Structure

### Master tab
One row per competitor. Column order matches `MASTER_HEADERS` in `tools/export_to_sheets.py`:

Domain | URL | Hero Text | Pricing Summary | # Pricing Tiers | # Features | Blog Active | Frontend Stack | Analytics | CDN | Payments | Hosting | GitHub Org | GitHub Stars (top repo) | Primary Languages | Top Keywords | OG Complete

### Per-competitor tabs (named by domain)
Sections written in order: OVERVIEW → PRICING → BLOG → TECH STACK → GITHUB → SEO

## Idempotency
Running the tool multiple times against the same sheet is safe — it clears and rewrites each tab on every run.

## Adding New Columns to Master
Edit `MASTER_HEADERS` (the list) and `build_master_row()` (the function) in `tools/export_to_sheets.py` together. The list index in `MASTER_HEADERS` must match the position in the returned list from `build_master_row()`.
