# Workflow: Scout

## Objective
Discover and research competitors for a given keyword or seed URL, then export all findings to a self-contained HTML report.

## Required Inputs
- At least one of:
  - `--query`: a keyword or product category (e.g. "AI writing tools")
  - `--url`: a known competitor URL to discover peers from (e.g. "https://writesonic.com")

## Automated Run (recommended)

```bash
python scout.py --url "https://company.com" [--query "KEYWORD"] [--max-competitors 5] [--export html|markdown|sheets]
```

Runs the full pipeline end-to-end and exports the report. No manual steps required.

## Manual Steps (step-by-step control)

### 1. Discover competitors
```bash
python tools/discover_competitors.py --query "YOUR KEYWORD" [--url "SEED_URL"]
```
Output: `.tmp/competitors.json`. Open it, review the list, and remove any false positives before continuing.

### 2. For each competitor in `.tmp/competitors.json`

Run these four tools in sequence, substituting `{url}`, `{domain}`, and `{name}` from each entry:

```bash
python tools/scrape_competitor.py --url "{url}"
python tools/detect_tech_stack.py --url "{url}"
python tools/fetch_github_presence.py --company "{name}" --domain "{domain}"
python tools/analyze_seo.py --domain "{domain}"
```

Check `.tmp/errors.json` after each competitor. Surface any failures before continuing to the next.

### 3. Export
```bash
python tools/export_to_html.py [--output "path/to/report.html"]
```
Output: `.tmp/competitor_analysis.html` (default). Open directly in any browser — no server needed, fully self-contained.

### 4. Report back
After export, summarize:
- Which competitors were fully researched
- Which had partial data (pricing not found, no GitHub, etc.)
- Which should be retried

## Edge Cases

| Situation | Action |
|-----------|--------|
| Site blocks Playwright | `scrape_competitor.py` auto-falls back to `requests`; if still failing, log and continue to next competitor |
| Pricing page not found | `pricing.found = false`; export will show "Not found" |
| No GitHub presence | `github.found = false`; GitHub section shows "No GitHub presence found." in report |
| Rate limited (HTTP 429) | Wait 60 seconds, retry once; if still failing, skip and log |
| Cookie consent wall | Scraper auto-clicks Accept; if blocked, some data may be missing |
