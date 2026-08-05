# Competitor Research Framework — Tools & Workflows Design

**Date:** 2026-08-05
**Status:** Approved

## Overview

Build out the `tools/` and `workflows/` directories for the Automated Web Content and Competitor Research project, following the WAT framework. The system accepts a keyword or competitor URL as input, dynamically discovers competitors, extracts comprehensive intelligence on each, and exports results to Google Sheets — all using free libraries and APIs, triggered manually by the user.

---

## Architecture

### Data Flow

```
[Input: keyword or URL]
        ↓
discover_competitors.py
        ↓
.tmp/competitors.json  ←— review & prune before continuing
        ↓ (for each competitor)
┌────────────────────────────────────┐
│ scrape_competitor.py               │ → .tmp/scraped/{domain}.json
│ detect_tech_stack.py               │ → .tmp/techstack/{domain}.json
│ fetch_github_presence.py           │ → .tmp/github/{domain}.json
└────────────────────────────────────┘
        ↓
analyze_seo.py (reads scrape output, no re-fetch)
        ↓
.tmp/seo/{domain}.json
        ↓
export_to_sheets.py
        ↓
[Google Sheets: Master tab + one tab per competitor]
```

### Directory Layout

```
tools/
  discover_competitors.py
  scrape_competitor.py
  detect_tech_stack.py
  fetch_github_presence.py
  analyze_seo.py
  export_to_sheets.py

workflows/
  research_competitors.md      # master end-to-end SOP
  scrape_website.md            # single-site scraping reference
  export_to_google_sheets.md   # Sheets setup + runtime SOP

.tmp/
  competitors.json
  errors.json
  scraped/{domain}.json
  techstack/{domain}.json
  github/{domain}.json
  seo/{domain}.json
```

---

## Tool Specifications

### `discover_competitors.py`

**Purpose:** Discover competitor URLs from a keyword, seed URL, or both.

**Args:**
- `--query "AI writing tools"` — search DuckDuckGo for top results + alternatives/comparisons
- `--url "competitor.com"` — fetch page, extract description, derive search terms, then discover peers
- Both flags can be used together

**Logic:**
1. If `--url` given: fetch homepage, extract meta description + H1, build search queries from them
2. Search DuckDuckGo using: `[query]`, `[query] alternatives`, `best [query] tools`
3. Collect top organic results, filter out noise domains (Wikipedia, Reddit, Quora, YouTube, G2, Capterra, review aggregators)
4. Deduplicate by domain
5. Write `.tmp/competitors.json`

**Output format (`.tmp/competitors.json`):**
```json
[
  {
    "name": "Company Name",
    "url": "https://company.com",
    "domain": "company.com",
    "discovered_via": "keyword: AI writing tools"
  }
]
```

**Libraries:** `duckduckgo-search`, `requests`, `beautifulsoup4`, `python-dotenv`

---

### `scrape_competitor.py`

**Purpose:** Scrape pricing, features, blog content, and ad/marketing copy from a competitor site.

**Args:**
- `--url "https://company.com"`

**Logic:**
1. Launch Playwright (headless Chromium), navigate to homepage
2. Extract: hero text, primary CTA copy, meta description, OG tags
3. Auto-discover nav links to `/pricing`, `/features`, `/product`, `/blog` (fuzzy match)
4. Visit pricing page: extract tier names, prices, feature bullets per tier
5. Visit features page: extract feature headings and descriptions
6. Visit blog: extract latest 5 post titles, dates, summaries
7. Add 1–2 second delay between page loads
8. On cookie consent walls: click accept if visible, otherwise proceed
9. Fallback: if Playwright is blocked (bot detection), retry with `requests` + BeautifulSoup on static content

**Output format (`.tmp/scraped/{domain}.json`):**
```json
{
  "domain": "company.com",
  "url": "https://company.com",
  "scraped_at": "ISO timestamp",
  "homepage": {
    "hero_text": "...",
    "cta_text": "...",
    "meta_description": "...",
    "og_title": "...",
    "og_description": "..."
  },
  "pricing": {
    "found": true,
    "url": "https://company.com/pricing",
    "tiers": [{"name": "Pro", "price": "$49/mo", "features": [...]}]
  },
  "features": {"found": true, "url": "...", "items": [...]},
  "blog": {"found": true, "url": "...", "posts": [{"title": "...", "date": "...", "summary": "..."}]},
  "raw_html": "<!DOCTYPE html>..."
}
```

**Libraries:** `playwright`, `beautifulsoup4`, `requests`, `python-dotenv`

---

### `detect_tech_stack.py`

**Purpose:** Identify the technologies a competitor uses.

**Args:**
- `--url "https://company.com"`

**Logic:**
1. Fetch homepage with `requests` (preserves response headers)
2. Pass HTML + headers to `python-wappalyzer` for automated detection
3. Check additional signals:
   - `robots.txt` and `sitemap.xml` for platform hints
   - DNS MX records for email provider (Google Workspace, Microsoft 365, etc.)
   - Common path probes: `/_next/` (Next.js), `/wp-admin` (WordPress), `/ghost/` (Ghost)
   - Response headers: `x-powered-by`, `server`, `x-generator`
4. Categorize results: frontend framework, backend/CMS, analytics, CDN, hosting, payments, email, customer support

**Output format (`.tmp/techstack/{domain}.json`):**
```json
{
  "domain": "company.com",
  "detected_at": "ISO timestamp",
  "stack": {
    "frontend": ["React", "Next.js"],
    "analytics": ["Google Analytics 4", "Hotjar"],
    "cdn": ["Cloudflare"],
    "payments": ["Stripe"],
    "email": ["Google Workspace"],
    "support": ["Intercom"],
    "hosting": ["Vercel"]
  },
  "raw_wappalyzer": {...}
}
```

**Libraries:** `python-wappalyzer`, `requests`, `dnspython`, `python-dotenv`

---

### `fetch_github_presence.py`

**Purpose:** Find a competitor's open-source footprint on GitHub.

**Args:**
- `--company "CompanyName"`
- `--domain "company.com"`

**Logic:**
1. Search GitHub API for organizations matching company name
2. Check if company website links to a GitHub org (look for github.com links in homepage HTML)
3. If org found: fetch public repos, sort by stars, collect top 10
4. Extract: org description, public repo count, top repos (name, description, stars, language, last push), primary languages across all repos
5. If no org found: search repos by company name, note result as "inferred"

**Requires:** `GITHUB_TOKEN` in `.env` (free personal access token — 5,000 req/hr authenticated vs 60/hr unauthenticated)

**Output format (`.tmp/github/{domain}.json`):**
```json
{
  "domain": "company.com",
  "fetched_at": "ISO timestamp",
  "found": true,
  "org": "company-github-org",
  "public_repos": 42,
  "top_repos": [{"name": "...", "stars": 1200, "language": "TypeScript", "description": "..."}],
  "primary_languages": ["TypeScript", "Python", "Go"],
  "last_activity": "2026-07-15"
}
```

**Libraries:** `PyGithub`, `requests`, `python-dotenv`

---

### `analyze_seo.py`

**Purpose:** Extract SEO signals from already-scraped HTML — no additional network requests.

**Args:**
- `--domain "company.com"` — reads `.tmp/scraped/{domain}.json`

**Logic:**
1. Parse homepage HTML from scrape output
2. Extract: title tag, meta description, canonical URL, H1–H3 headings, keyword frequency (top 20 non-stopword terms), internal vs external link count, image alt text presence, schema.org structured data types, Open Graph completeness

**Output format (`.tmp/seo/{domain}.json`):**
```json
{
  "domain": "company.com",
  "analyzed_at": "ISO timestamp",
  "title": "...",
  "meta_description": "...",
  "canonical": "...",
  "headings": {"h1": [...], "h2": [...], "h3": [...]},
  "top_keywords": [{"term": "writing", "count": 14}],
  "links": {"internal": 32, "external": 8},
  "schema_types": ["Organization", "Product"],
  "og_complete": true
}
```

**Libraries:** `beautifulsoup4`, `lxml`, `python-dotenv`

---

### `export_to_sheets.py`

**Purpose:** Write all `.tmp/` research data to Google Sheets.

**Args:**
- `--sheet-id "GOOGLE_SHEET_ID"` — optional; creates a new sheet if omitted

**Logic:**
1. Load all `.tmp/` JSON files, join by domain
2. Write **Tab 1 "Master"**: one row per competitor, columns — Name, URL, Pricing (summary), # Features, Blog Active, Tech Stack (summary), GitHub Stars, Top Keywords, Pricing Page Found
3. Write **one tab per competitor** named by domain: full pricing table, feature list, blog posts, complete tech stack, GitHub repos, SEO breakdown
4. If sheet already exists: clear and rewrite (idempotent)

**Requires:** `credentials.json` + `token.json` (Google OAuth). Setup documented in `workflows/export_to_google_sheets.md`.

**Libraries:** `google-api-python-client`, `google-auth`, `google-auth-oauthlib`, `pandas`, `python-dotenv`

---

## Workflow Specifications

### `workflows/research_competitors.md`

Master end-to-end SOP. Covers:
- Confirm input type (keyword, URL, or both) and target Sheet ID
- Run `discover_competitors.py`, review `.tmp/competitors.json`, remove false positives before proceeding
- For each confirmed competitor: run `scrape_competitor.py` → `detect_tech_stack.py` → `fetch_github_presence.py` → `analyze_seo.py`
- Run `export_to_sheets.py`
- Report: successes, failures with reasons, what to retry
- Edge cases: site blocks Playwright (try requests fallback), no GitHub presence (skip + log), pricing page not found (note as "pricing not public"), rate limiting (add delay, retry once)

### `workflows/scrape_website.md`

Reference SOP for `scrape_competitor.py`. Covers: Playwright navigation approach, handling cookie/consent walls, paywalled content (skip, note), rate limit behavior (1–2s delay between pages), static-site fallback with requests + BeautifulSoup, what counts as a "pricing page" vs a "contact sales" page.

### `workflows/export_to_google_sheets.md`

One-time setup: create Google Cloud project, enable Sheets + Drive APIs, create OAuth credentials, download `credentials.json`. Runtime SOP: running `export_to_sheets.py`, first-run browser auth flow (generates `token.json`), expected Sheet structure, how to extend columns.

---

## Error Handling

- All tools catch page-level failures and write partial data rather than crashing
- Errors logged to `.tmp/errors.json` with domain, tool, error message, and timestamp
- The master workflow checks `errors.json` after each tool run and surfaces failures to the user before proceeding to export

---

## Environment Variables (`.env`)

```
GITHUB_TOKEN=your_personal_access_token    # github.com/settings/tokens → "Fine-grained" or classic
GOOGLE_SHEET_ID=                           # optional; leave blank to auto-create
```

No paid API keys required.

---

## Dependencies

Install all at once:
```bash
pip install duckduckgo-search playwright python-wappalyzer beautifulsoup4 lxml \
            requests dnspython PyGithub google-api-python-client google-auth \
            google-auth-oauthlib pandas python-dotenv
playwright install chromium
```
