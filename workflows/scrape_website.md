# Workflow: Scrape Website

## Objective
Scrape a single competitor website for marketing copy, pricing, features, and blog content.

## Tool
```bash
python tools/scrape_competitor.py --url "https://company.com"
```
Output: `.tmp/scraped/{domain}.json`

## How the Scraper Works

1. Launches headless Chromium via Playwright
2. Navigates to the homepage and waits for `networkidle`
3. Auto-clicks cookie consent buttons if present (checks for "Accept", "Accept all")
4. Extracts hero H1, CTA text, meta description, OG tags from homepage
5. Scans all `<a href>` elements for nav links to pricing/features/blog pages (fuzzy path match)
6. Visits each discovered page with a 1.5-second delay between loads
7. Falls back to `requests` + BeautifulSoup if Playwright raises an exception

## What Counts as a Pricing Page
A URL path containing `pricing`, `price`, `plans`, or `subscription`. A page showing only "Contact sales" with no dollar amounts will be scraped — the `price` field for those tiers will read "Contact sales".

## Handling Paywalled Content
If a page requires login, the scraper captures whatever is publicly visible. Do not attempt to log in — the result will have `found: true` but empty data arrays.

## Static Site Fallback
If Playwright fails (bot detection, timeout, browser crash), the tool retries the homepage with `requests`. Sub-pages (pricing, features, blog) will not be available in this mode — their `found` field will be `false`.

## Rate Limiting
The tool adds a 1.5-second delay between page loads. If you receive a 429 response, wait 60 seconds and re-run the tool for that domain.

## The `raw_html` Field
The homepage HTML is stored in `raw_html` so that `analyze_seo.py` can parse it without a second network request. Do not remove this field from the output.
