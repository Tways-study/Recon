# Recon

Competitor intelligence pipeline. Given a URL or keyword, Scout discovers competitors and produces a research report covering marketing copy, pricing, tech stack, GitHub presence, and SEO signals.

## Quickstart

```bash
pip install -r requirements.txt
playwright install chromium

# Full pipeline — outputs an HTML report
python scout.py --url https://writesonic.com
python scout.py --query "AI writing tools" --max-competitors 8
python scout.py --url https://notion.so --export sheets
```

`--export` accepts `html` (default), `markdown`, or `sheets`.

## What It Collects

| Signal | Source |
|--------|--------|
| Hero text, pricing tiers, features, blog activity | Playwright scrape (falls back to requests) |
| Frontend framework, analytics, CDN, payments, hosting | Wappalyzer + DNS |
| GitHub org, top repo stars, primary languages | GitHub API |
| Title, meta description, OG tags, keyword density | Scraped HTML |

## Setup

1. Copy `.env.example` to `.env` and fill in your tokens:
   ```
   GITHUB_TOKEN=       # read-only PAT; unauthenticated rate limit is 60 req/hour
   GOOGLE_SHEET_ID=    # optional; omit to create a new sheet automatically
   ```
2. For Google Sheets export, complete the one-time OAuth flow described in `workflows/export_to_google_sheets.md`.

## Manual Pipeline

If you want step-by-step control (e.g., to review the competitor list before proceeding):

```bash
# 1. Discover — review .tmp/competitors.json before continuing
python tools/discover_competitors.py --query "AI writing tools"

# 2. Research each competitor
python tools/scrape_competitor.py --url "https://competitor.com"
python tools/detect_tech_stack.py --url "https://competitor.com"
python tools/fetch_github_presence.py --company "Competitor" --domain "competitor.com"
python tools/analyze_seo.py --domain "competitor.com"   # requires scrape first

# 3. Export
python tools/export_to_html.py
```

Check `.tmp/errors.json` after each step — failed tools log there and don't abort the pipeline.

## Tests

```bash
pytest
pytest tests/test_discover_competitors.py::test_deduplicate_removes_duplicate_domain
```

All tests mock external services — no network calls.
