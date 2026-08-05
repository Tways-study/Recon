# Competitor Research Framework — Tools & Workflows Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build six Python tools and three workflow SOPs that take a keyword or URL as input, discover competitors, extract comprehensive intelligence (pricing, features, blog, tech stack, GitHub, SEO), and export results to Google Sheets.

**Architecture:** Each tool is a standalone Python script that reads inputs from CLI args and writes output to `.tmp/` as JSON. Tools are sequenced by the master workflow SOP; the agent (Claude) orchestrates which tools to call and in what order. No tool imports from another tool — they communicate only through `.tmp/` files.

**Tech Stack:** Python 3.11+, duckduckgo-search, playwright (Chromium), python-Wappalyzer, beautifulsoup4, lxml, requests, dnspython, PyGithub, google-api-python-client, pandas, python-dotenv, pytest, pytest-mock

## Global Constraints

- Python 3.11+ required (`str | None` union syntax used throughout)
- All tools catch exceptions at the top level and log to `.tmp/errors.json` rather than crashing
- All `.tmp/` paths use `Path` objects, never string concatenation
- All JSON output uses `json.dumps(data, indent=2)`
- Domain is always the last two parts of a hostname (`notion.so` not `www.notion.so`)
- Timestamps are ISO 8601 UTC: `datetime.now(timezone.utc).isoformat()`
- No tool imports from another tool — shared helpers (`extract_domain`, `log_error`) are duplicated per-file

---

### Task 1: Project scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `tests/conftest.py`

**Interfaces:**
- Produces: importable `tools/` package via `sys.path` insertion in `tests/conftest.py`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p tools workflows tests .tmp/scraped .tmp/techstack .tmp/github .tmp/seo
```

- [ ] **Step 2: Write `requirements.txt`**

```
duckduckgo-search>=6.2.0
playwright>=1.44.0
python-Wappalyzer>=0.3.1
beautifulsoup4>=4.12.0
lxml>=5.0.0
requests>=2.31.0
dnspython>=2.6.0
PyGithub>=2.3.0
google-api-python-client>=2.130.0
google-auth>=2.29.0
google-auth-oauthlib>=1.2.0
pandas>=2.2.0
python-dotenv>=1.0.0
pytest>=8.0.0
pytest-mock>=3.14.0
```

- [ ] **Step 3: Write `.env.example`**

```
GITHUB_TOKEN=your_personal_access_token
GOOGLE_SHEET_ID=
```

- [ ] **Step 4: Write `.gitignore`**

```
.env
credentials.json
token.json
__pycache__/
*.pyc
.pytest_cache/
.tmp/
```

- [ ] **Step 5: Write `tests/conftest.py`**

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
```

- [ ] **Step 6: Install dependencies**

```bash
pip install -r requirements.txt
playwright install chromium
```

Expected: all packages install without error.

- [ ] **Step 7: Commit**

```bash
git add requirements.txt .env.example .gitignore tests/conftest.py
git commit -m "chore: project scaffolding — deps, dirs, gitignore"
```

---

### Task 2: discover_competitors.py

**Files:**
- Create: `tools/discover_competitors.py`
- Create: `tests/test_discover_competitors.py`

**Interfaces:**
- Produces: `.tmp/competitors.json` — list of `{name, url, domain, discovered_via}`
- Produces: CLI `python tools/discover_competitors.py --query "X" [--url "Y"]`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_discover_competitors.py`:

```python
import json
from unittest.mock import MagicMock, patch

from tools.discover_competitors import (
    build_queries,
    deduplicate,
    extract_domain,
    is_noise_domain,
    parse_seed_url,
    search_ddg,
)


def test_extract_domain_full_url():
    assert extract_domain("https://www.notion.so/pricing") == "notion.so"


def test_extract_domain_no_scheme():
    assert extract_domain("notion.so") == "notion.so"


def test_is_noise_domain_known_noise():
    assert is_noise_domain("wikipedia.org") is True


def test_is_noise_domain_subdomain_of_noise():
    assert is_noise_domain("en.wikipedia.org") is True


def test_is_noise_domain_real_company():
    assert is_noise_domain("notion.so") is False


def test_deduplicate_removes_duplicate_domain():
    competitors = [
        {"domain": "notion.so", "url": "https://notion.so", "name": "Notion", "discovered_via": "q1"},
        {"domain": "notion.so", "url": "https://notion.so/pricing", "name": "Notion 2", "discovered_via": "q2"},
    ]
    result = deduplicate(competitors)
    assert len(result) == 1
    assert result[0]["url"] == "https://notion.so"


def test_deduplicate_keeps_unique_domains():
    competitors = [
        {"domain": "notion.so", "url": "https://notion.so", "name": "Notion", "discovered_via": "q1"},
        {"domain": "coda.io", "url": "https://coda.io", "name": "Coda", "discovered_via": "q1"},
    ]
    assert len(deduplicate(competitors)) == 2


def test_build_queries():
    queries = build_queries("project management software")
    assert queries == [
        "project management software",
        "project management software alternatives",
        "best project management software tools",
    ]


def test_parse_seed_url_uses_meta_description():
    html = '<html><head><meta name="description" content="The best workspace"></head><body></body></html>'
    assert parse_seed_url(html, "https://notion.so") == "The best workspace"


def test_parse_seed_url_falls_back_to_h1():
    html = "<html><head></head><body><h1>All-in-one workspace</h1></body></html>"
    assert parse_seed_url(html, "https://notion.so") == "All-in-one workspace"


def test_parse_seed_url_falls_back_to_domain():
    html = "<html><head></head><body></body></html>"
    assert parse_seed_url(html, "https://notion.so") == "notion.so"


@patch("tools.discover_competitors.DDGS")
def test_search_ddg_filters_noise_domains(mock_ddgs_class):
    mock_ddgs = MagicMock()
    mock_ddgs_class.return_value.__enter__.return_value = mock_ddgs
    mock_ddgs.text.return_value = [
        {"href": "https://notion.so", "title": "Notion"},
        {"href": "https://reddit.com/r/productivity", "title": "Reddit thread"},
    ]
    results = search_ddg("note taking app")
    assert len(results) == 1
    assert results[0]["domain"] == "notion.so"


@patch("tools.discover_competitors.DDGS")
def test_search_ddg_sets_discovered_via(mock_ddgs_class):
    mock_ddgs = MagicMock()
    mock_ddgs_class.return_value.__enter__.return_value = mock_ddgs
    mock_ddgs.text.return_value = [{"href": "https://notion.so", "title": "Notion"}]
    results = search_ddg("note app")
    assert results[0]["discovered_via"] == "query: note app"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_discover_competitors.py -v
```

Expected: `ModuleNotFoundError: No module named 'tools.discover_competitors'`

- [ ] **Step 3: Implement `tools/discover_competitors.py`**

```python
#!/usr/bin/env python3
"""Discover competitor URLs from a keyword, seed URL, or both."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from dotenv import load_dotenv

load_dotenv()

TMP_DIR = Path(".tmp")

NOISE_DOMAINS = {
    "wikipedia.org", "reddit.com", "quora.com", "youtube.com",
    "g2.com", "capterra.com", "trustpilot.com", "producthunt.com",
    "techcrunch.com", "forbes.com", "linkedin.com", "twitter.com",
    "x.com", "facebook.com", "instagram.com", "medium.com",
    "getapp.com", "softwareadvice.com", "alternativeto.net",
    "yelp.com", "glassdoor.com", "crunchbase.com",
}


def extract_domain(url: str) -> str:
    parsed = urlparse(url if url.startswith("http") else f"https://{url}")
    host = parsed.netloc or parsed.path
    parts = host.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def is_noise_domain(domain: str) -> bool:
    return any(domain == noise or domain.endswith(f".{noise}") for noise in NOISE_DOMAINS)


def deduplicate(competitors: list[dict]) -> list[dict]:
    seen: set[str] = set()
    result = []
    for c in competitors:
        if c["domain"] not in seen:
            seen.add(c["domain"])
            result.append(c)
    return result


def parse_seed_url(html: str, url: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        return meta["content"][:100]
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)[:100]
    return extract_domain(url)


def build_queries(base_query: str) -> list[str]:
    return [
        base_query,
        f"{base_query} alternatives",
        f"best {base_query} tools",
    ]


def search_ddg(query: str, max_results: int = 10) -> list[dict]:
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            url = r.get("href", "")
            if not url:
                continue
            domain = extract_domain(url)
            if not is_noise_domain(domain):
                results.append({
                    "name": r.get("title", domain),
                    "url": url,
                    "domain": domain,
                    "discovered_via": f"query: {query}",
                })
    return results


def log_error(domain: str, tool: str, message: str) -> None:
    errors_file = TMP_DIR / "errors.json"
    errors = json.loads(errors_file.read_text()) if errors_file.exists() else []
    errors.append({
        "domain": domain,
        "tool": tool,
        "error": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    errors_file.write_text(json.dumps(errors, indent=2))


def discover(query: str | None = None, url: str | None = None) -> list[dict]:
    base_query = query or ""
    if url:
        seed_url = url if url.startswith("http") else f"https://{url}"
        resp = requests.get(seed_url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        seed_query = parse_seed_url(resp.text, url)
        base_query = f"{base_query} {seed_query}".strip()

    all_results: list[dict] = []
    for q in build_queries(base_query):
        all_results.extend(search_ddg(q))

    return deduplicate(all_results)


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover competitors from a keyword or seed URL.")
    parser.add_argument("--query", help="Search keyword or phrase")
    parser.add_argument("--url", help="Seed competitor URL")
    args = parser.parse_args()

    if not args.query and not args.url:
        parser.error("Provide at least one of --query or --url")

    TMP_DIR.mkdir(exist_ok=True)

    try:
        competitors = discover(query=args.query, url=args.url)
        output = TMP_DIR / "competitors.json"
        output.write_text(json.dumps(competitors, indent=2))
        print(f"Found {len(competitors)} competitors → {output}")
        for c in competitors:
            print(f"  {c['domain']}")
    except Exception as e:
        log_error("", "discover_competitors", str(e))
        raise


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_discover_competitors.py -v
```

Expected: all 12 tests PASS

- [ ] **Step 5: Commit**

```bash
git add tools/discover_competitors.py tests/test_discover_competitors.py
git commit -m "feat: add discover_competitors tool with DuckDuckGo search"
```

---

### Task 3: scrape_competitor.py

**Files:**
- Create: `tools/scrape_competitor.py`
- Create: `tests/test_scrape_competitor.py`

**Interfaces:**
- Consumes: `--url "https://company.com"` CLI arg
- Produces: `.tmp/scraped/{domain}.json` — `{domain, url, scraped_at, homepage, pricing, features, blog, raw_html}`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_scrape_competitor.py`:

```python
from tools.scrape_competitor import (
    extract_domain,
    extract_blog_data,
    extract_features_data,
    extract_homepage_data,
    extract_pricing_data,
    find_nav_link,
)

HOMEPAGE_HTML = """
<html>
<head>
  <meta name="description" content="The best writing tool">
  <meta property="og:title" content="Writesonic">
  <meta property="og:description" content="AI writing assistant">
</head>
<body>
  <h1>Write better content faster</h1>
  <a href="/pricing">Get started free</a>
</body>
</html>
"""

PRICING_HTML = """
<html><body>
  <div class="plan">
    <h3>Starter</h3>
    <p>$19/mo</p>
    <ul><li>10,000 words</li><li>5 users</li></ul>
  </div>
  <div class="plan">
    <h3>Pro</h3>
    <p>$49/mo</p>
    <ul><li>Unlimited words</li></ul>
  </div>
</body></html>
"""

FEATURES_HTML = """
<html><body>
  <h2>AI Writing</h2><p>Generate content in seconds</p>
  <h2>SEO Optimizer</h2><p>Rank higher in search</p>
</body></html>
"""

BLOG_HTML = """
<html><body>
  <article class="post">
    <h3>Top 10 AI Writing Tips</h3>
    <time class="date">2026-07-01</time>
    <p>Here are the best tips for writing with AI...</p>
  </article>
  <article class="post">
    <h3>How to Write Faster</h3>
    <time class="date">2026-06-15</time>
    <p>Speed up your writing process with these strategies...</p>
  </article>
</body></html>
"""


def test_extract_domain():
    assert extract_domain("https://www.writesonic.com/pricing") == "writesonic.com"


def test_extract_homepage_meta_description():
    data = extract_homepage_data(HOMEPAGE_HTML, "https://writesonic.com")
    assert data["meta_description"] == "The best writing tool"


def test_extract_homepage_og_title():
    data = extract_homepage_data(HOMEPAGE_HTML, "https://writesonic.com")
    assert data["og_title"] == "Writesonic"


def test_extract_homepage_hero_text():
    data = extract_homepage_data(HOMEPAGE_HTML, "https://writesonic.com")
    assert data["hero_text"] == "Write better content faster"


def test_extract_homepage_cta():
    data = extract_homepage_data(HOMEPAGE_HTML, "https://writesonic.com")
    assert "free" in data["cta_text"].lower()


def test_extract_pricing_finds_tiers():
    data = extract_pricing_data(PRICING_HTML, "https://writesonic.com/pricing")
    assert data["found"] is True
    assert len(data["tiers"]) == 2


def test_extract_pricing_tier_names():
    data = extract_pricing_data(PRICING_HTML, "https://writesonic.com/pricing")
    names = [t["name"] for t in data["tiers"]]
    assert "Starter" in names
    assert "Pro" in names


def test_extract_pricing_tier_prices():
    data = extract_pricing_data(PRICING_HTML, "https://writesonic.com/pricing")
    starter = next(t for t in data["tiers"] if t["name"] == "Starter")
    assert "$19/mo" in starter["price"]


def test_extract_features_items():
    data = extract_features_data(FEATURES_HTML, "https://writesonic.com/features")
    assert data["found"] is True
    headings = [i["heading"] for i in data["items"]]
    assert "AI Writing" in headings
    assert "SEO Optimizer" in headings


def test_extract_blog_posts():
    data = extract_blog_data(BLOG_HTML, "https://writesonic.com/blog")
    assert data["found"] is True
    assert len(data["posts"]) == 2
    assert data["posts"][0]["title"] == "Top 10 AI Writing Tips"


def test_find_nav_link_matches_keyword():
    links = ["https://writesonic.com/about", "https://writesonic.com/pricing", "https://writesonic.com/blog"]
    result = find_nav_link(links, ["pricing", "price", "plans"], "https://writesonic.com")
    assert result == "https://writesonic.com/pricing"


def test_find_nav_link_returns_none_when_missing():
    links = ["https://writesonic.com/about", "https://writesonic.com/contact"]
    result = find_nav_link(links, ["pricing", "plans"], "https://writesonic.com")
    assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_scrape_competitor.py -v
```

Expected: `ModuleNotFoundError: No module named 'tools.scrape_competitor'`

- [ ] **Step 3: Implement `tools/scrape_competitor.py`**

```python
#!/usr/bin/env python3
"""Scrape pricing, features, blog, and marketing copy from a competitor site."""

import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

TMP_DIR = Path(".tmp")
SCRAPED_DIR = TMP_DIR / "scraped"
PAGE_DELAY = 1.5

NAV_KEYWORDS = {
    "pricing": ["pricing", "price", "plans", "subscription"],
    "features": ["features", "product", "solutions", "capabilities"],
    "blog": ["blog", "articles", "insights", "resources", "news"],
}


def extract_domain(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc
    parts = host.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def find_nav_link(links: list[str], keywords: list[str], base_url: str) -> str | None:
    for link in links:
        path = urlparse(link).path.lower().rstrip("/")
        if any(kw in path for kw in keywords):
            return link
    return None


def extract_homepage_data(html: str, page_url: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    meta_desc = ""
    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag:
        meta_desc = meta_tag.get("content", "")
    og_title = ""
    og_tag = soup.find("meta", property="og:title")
    if og_tag:
        og_title = og_tag.get("content", "")
    og_desc = ""
    og_desc_tag = soup.find("meta", property="og:description")
    if og_desc_tag:
        og_desc = og_desc_tag.get("content", "")
    h1 = soup.find("h1")
    hero_text = h1.get_text(strip=True) if h1 else ""
    cta = ""
    for tag in soup.find_all(["a", "button"]):
        text = tag.get_text(strip=True)
        if text and len(text) < 50 and any(w in text.lower() for w in ["start", "get", "try", "sign", "free", "demo"]):
            cta = text
            break
    return {
        "hero_text": hero_text,
        "cta_text": cta,
        "meta_description": meta_desc,
        "og_title": og_title,
        "og_description": og_desc,
    }


def extract_pricing_data(html: str, page_url: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    price_pattern = re.compile(r"\$[\d,]+(?:\.\d{2})?(?:/(?:mo|month|yr|year))?", re.IGNORECASE)
    tiers = []
    for card in soup.find_all(["section", "div", "article"], class_=re.compile(r"plan|tier|price|card", re.I)):
        name_tag = card.find(["h2", "h3", "h4"])
        name = name_tag.get_text(strip=True) if name_tag else ""
        price_match = price_pattern.search(card.get_text())
        price = price_match.group(0) if price_match else "Contact sales"
        features = [li.get_text(strip=True) for li in card.find_all("li") if li.get_text(strip=True)]
        if name:
            tiers.append({"name": name, "price": price, "features": features})
    return {"found": bool(tiers), "url": page_url, "tiers": tiers}


def extract_features_data(html: str, page_url: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    items = []
    for heading in soup.find_all(["h2", "h3"]):
        text = heading.get_text(strip=True)
        if text and len(text) > 3:
            sibling = heading.find_next_sibling(["p", "div"])
            desc = sibling.get_text(strip=True)[:200] if sibling else ""
            items.append({"heading": text, "description": desc})
    return {"found": bool(items), "url": page_url, "items": items}


def extract_blog_data(html: str, page_url: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    posts = []
    for article in soup.find_all(["article", "div"], class_=re.compile(r"post|article|blog|card", re.I))[:5]:
        title_tag = article.find(["h2", "h3", "h4", "a"])
        title = title_tag.get_text(strip=True) if title_tag else ""
        date_tag = article.find(["time", "span"], class_=re.compile(r"date|time|publish", re.I))
        date = date_tag.get_text(strip=True) if date_tag else ""
        summary_tag = article.find("p")
        summary = summary_tag.get_text(strip=True)[:200] if summary_tag else ""
        if title:
            posts.append({"title": title, "date": date, "summary": summary})
    return {"found": bool(posts), "url": page_url, "posts": posts}


def _click_cookie_consent(page) -> None:
    for selector in ["button:has-text('Accept')", "button:has-text('Accept all')", "#cookie-accept", ".accept-cookies"]:
        try:
            btn = page.query_selector(selector)
            if btn and btn.is_visible():
                btn.click()
                page.wait_for_timeout(500)
                return
        except Exception:
            pass


def scrape(url: str) -> dict:
    domain = extract_domain(url)
    base_url = url if url.startswith("http") else f"https://{url}"

    result: dict = {
        "domain": domain,
        "url": base_url,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "homepage": {},
        "pricing": {"found": False, "url": None, "tiers": []},
        "features": {"found": False, "url": None, "items": []},
        "blog": {"found": False, "url": None, "posts": []},
        "raw_html": "",
    }

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent="Mozilla/5.0 (compatible; ResearchBot/1.0)")
            page = context.new_page()
            page.goto(base_url, timeout=30000)
            page.wait_for_load_state("networkidle", timeout=15000)
            _click_cookie_consent(page)
            html = page.content()
            result["raw_html"] = html
            result["homepage"] = extract_homepage_data(html, base_url)
            links = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
            time.sleep(PAGE_DELAY)

            for section, keywords in NAV_KEYWORDS.items():
                nav_url = find_nav_link(links, keywords, base_url)
                if nav_url:
                    try:
                        page.goto(nav_url, timeout=20000)
                        page.wait_for_load_state("networkidle", timeout=10000)
                        section_html = page.content()
                        time.sleep(PAGE_DELAY)
                        if section == "pricing":
                            result["pricing"] = extract_pricing_data(section_html, nav_url)
                        elif section == "features":
                            result["features"] = extract_features_data(section_html, nav_url)
                        elif section == "blog":
                            result["blog"] = extract_blog_data(section_html, nav_url)
                    except Exception as e:
                        result[section] = {"found": False, "url": nav_url, "error": str(e)}

            browser.close()
    except Exception:
        resp = requests.get(base_url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        html = resp.text
        result["raw_html"] = html
        result["homepage"] = extract_homepage_data(html, base_url)

    return result


def log_error(domain: str, tool: str, message: str) -> None:
    errors_file = TMP_DIR / "errors.json"
    errors = json.loads(errors_file.read_text()) if errors_file.exists() else []
    errors.append({
        "domain": domain,
        "tool": tool,
        "error": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    errors_file.write_text(json.dumps(errors, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape a competitor website.")
    parser.add_argument("--url", required=True, help="Competitor URL to scrape")
    args = parser.parse_args()

    TMP_DIR.mkdir(exist_ok=True)
    SCRAPED_DIR.mkdir(exist_ok=True)
    domain = extract_domain(args.url)

    try:
        data = scrape(args.url)
        output = SCRAPED_DIR / f"{domain}.json"
        output.write_text(json.dumps(data, indent=2))
        print(f"Scraped {domain} → {output}")
    except Exception as e:
        log_error(domain, "scrape_competitor", str(e))
        raise


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_scrape_competitor.py -v
```

Expected: all 12 tests PASS

- [ ] **Step 5: Commit**

```bash
git add tools/scrape_competitor.py tests/test_scrape_competitor.py
git commit -m "feat: add scrape_competitor tool with Playwright + BS4 fallback"
```

---

### Task 4: detect_tech_stack.py

**Files:**
- Create: `tools/detect_tech_stack.py`
- Create: `tests/test_detect_tech_stack.py`

**Interfaces:**
- Consumes: `--url "https://company.com"` CLI arg
- Produces: `.tmp/techstack/{domain}.json` — `{domain, detected_at, stack, raw_wappalyzer}`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_detect_tech_stack.py`:

```python
from unittest.mock import MagicMock

from tools.detect_tech_stack import (
    categorize_technologies,
    extract_domain,
    infer_email_provider,
    probe_path_hints,
)


def test_extract_domain():
    assert extract_domain("https://www.linear.app/pricing") == "linear.app"


def test_categorize_puts_react_in_frontend():
    raw = {"React": {"categories": ["JavaScript frameworks"]}}
    assert "React" in categorize_technologies(raw)["frontend"]


def test_categorize_puts_ga_in_analytics():
    raw = {"Google Analytics": {"categories": ["Analytics"]}}
    assert "Google Analytics" in categorize_technologies(raw)["analytics"]


def test_categorize_puts_cloudflare_in_cdn():
    raw = {"Cloudflare": {"categories": ["CDN"]}}
    assert "Cloudflare" in categorize_technologies(raw)["cdn"]


def test_categorize_puts_stripe_in_payments():
    raw = {"Stripe": {"categories": ["Payment processors"]}}
    assert "Stripe" in categorize_technologies(raw)["payments"]


def test_categorize_puts_wordpress_in_cms():
    raw = {"WordPress": {"categories": ["CMS", "Blog"]}}
    assert "WordPress" in categorize_technologies(raw)["cms"]


def test_categorize_unknown_goes_to_other():
    raw = {"SomeNewTool": {"categories": ["Something unknown"]}}
    assert "SomeNewTool" in categorize_technologies(raw)["other"]


def test_infer_email_provider_google():
    assert infer_email_provider(["aspmx.l.google.com"]) == "Google Workspace"


def test_infer_email_provider_microsoft():
    assert infer_email_provider(["company.mail.protection.outlook.com"]) == "Microsoft 365"


def test_infer_email_provider_unknown():
    assert infer_email_provider(["mail.somehost.com"]) == "Unknown"


def test_probe_path_hints_detects_nextjs():
    def mock_head(url):
        r = MagicMock()
        r.status_code = 200 if "_next" in url else 404
        return r

    assert "Next.js" in probe_path_hints("https://linear.app", mock_head)


def test_probe_path_hints_detects_wordpress():
    def mock_head(url):
        r = MagicMock()
        r.status_code = 200 if "wp-admin" in url else 404
        return r

    assert "WordPress" in probe_path_hints("https://example.com", mock_head)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_detect_tech_stack.py -v
```

Expected: `ModuleNotFoundError: No module named 'tools.detect_tech_stack'`

- [ ] **Step 3: Implement `tools/detect_tech_stack.py`**

```python
#!/usr/bin/env python3
"""Identify technologies used by a competitor website."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

import dns.resolver
import requests
from dotenv import load_dotenv
from Wappalyzer import Wappalyzer, WebPage

load_dotenv()

TMP_DIR = Path(".tmp")
TECHSTACK_DIR = TMP_DIR / "techstack"

CATEGORY_MAP = {
    "JavaScript frameworks": "frontend",
    "UI frameworks": "frontend",
    "Web frameworks": "frontend",
    "CSS frameworks": "frontend",
    "Analytics": "analytics",
    "Tag managers": "analytics",
    "CDN": "cdn",
    "Payment processors": "payments",
    "CMS": "cms",
    "Blog": "cms",
    "Ecommerce": "cms",
    "PaaS": "hosting",
    "Hosting": "hosting",
    "Email": "email",
    "Email marketing": "email",
    "Live chat": "support",
    "CRM": "support",
    "Helpdesk": "support",
}

PATH_PROBES = {
    "/_next/static/": "Next.js",
    "/wp-admin/": "WordPress",
    "/ghost/": "Ghost",
    "/__nuxt/": "Nuxt.js",
}


def extract_domain(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc
    parts = host.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def categorize_technologies(raw: dict) -> dict:
    result: dict[str, list[str]] = {
        "frontend": [], "analytics": [], "cdn": [], "payments": [],
        "cms": [], "hosting": [], "email": [], "support": [], "other": [],
    }
    for tech, info in raw.items():
        categories = info.get("categories", [])
        placed = False
        for cat in categories:
            bucket = CATEGORY_MAP.get(cat)
            if bucket:
                result[bucket].append(tech)
                placed = True
                break
        if not placed:
            result["other"].append(tech)
    return result


def infer_email_provider(mx_hosts: list[str]) -> str:
    combined = " ".join(mx_hosts).lower()
    if "google" in combined:
        return "Google Workspace"
    if "outlook" in combined or "microsoft" in combined:
        return "Microsoft 365"
    if "mimecast" in combined:
        return "Mimecast"
    if "proofpoint" in combined:
        return "Proofpoint"
    return "Unknown"


def probe_path_hints(base_url: str, head_fn: Callable[[str], object] | None = None) -> list[str]:
    if head_fn is None:
        session = requests.Session()
        head_fn = lambda url: session.head(url, timeout=5, allow_redirects=False)

    found = []
    for path, tech in PATH_PROBES.items():
        try:
            resp = head_fn(base_url.rstrip("/") + path)
            if resp and getattr(resp, "status_code", 404) == 200:
                found.append(tech)
        except Exception:
            pass
    return found


def get_mx_hosts(domain: str) -> list[str]:
    try:
        answers = dns.resolver.resolve(domain, "MX")
        return [str(r.exchange).lower().rstrip(".") for r in answers]
    except Exception:
        return []


def detect(url: str) -> dict:
    domain = extract_domain(url)
    base_url = url if url.startswith("http") else f"https://{url}"
    result: dict = {
        "domain": domain,
        "detected_at": datetime.now(timezone.utc).isoformat(),
        "stack": {},
        "raw_wappalyzer": {},
    }

    try:
        resp = requests.get(base_url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        webpage = WebPage(base_url, resp.text, dict(resp.headers))
        wappalyzer = Wappalyzer.latest()
        raw = wappalyzer.analyze_with_categories(webpage)
        result["raw_wappalyzer"] = {k: v for k, v in raw.items()}
        stack = categorize_technologies(result["raw_wappalyzer"])
    except Exception:
        stack = {k: [] for k in ["frontend", "analytics", "cdn", "payments", "cms", "hosting", "email", "support", "other"]}

    for hint in probe_path_hints(base_url):
        if hint not in stack["frontend"]:
            stack["frontend"].append(hint)

    mx_hosts = get_mx_hosts(domain)
    if mx_hosts:
        provider = infer_email_provider(mx_hosts)
        if provider != "Unknown" and provider not in stack["email"]:
            stack["email"].append(provider)

    result["stack"] = stack
    return result


def log_error(domain: str, tool: str, message: str) -> None:
    errors_file = TMP_DIR / "errors.json"
    errors = json.loads(errors_file.read_text()) if errors_file.exists() else []
    errors.append({
        "domain": domain,
        "tool": tool,
        "error": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    errors_file.write_text(json.dumps(errors, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect tech stack of a competitor.")
    parser.add_argument("--url", required=True, help="Competitor URL")
    args = parser.parse_args()

    TMP_DIR.mkdir(exist_ok=True)
    TECHSTACK_DIR.mkdir(exist_ok=True)
    domain = extract_domain(args.url)

    try:
        data = detect(args.url)
        output = TECHSTACK_DIR / f"{domain}.json"
        output.write_text(json.dumps(data, indent=2))
        print(f"Detected stack for {domain} → {output}")
        for category, techs in data["stack"].items():
            if techs:
                print(f"  {category}: {', '.join(techs)}")
    except Exception as e:
        log_error(domain, "detect_tech_stack", str(e))
        raise


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_detect_tech_stack.py -v
```

Expected: all 12 tests PASS

- [ ] **Step 5: Commit**

```bash
git add tools/detect_tech_stack.py tests/test_detect_tech_stack.py
git commit -m "feat: add detect_tech_stack tool with Wappalyzer, DNS, path probes"
```

---

### Task 5: fetch_github_presence.py

**Files:**
- Create: `tools/fetch_github_presence.py`
- Create: `tests/test_fetch_github_presence.py`

**Interfaces:**
- Consumes: `--company "CompanyName"` and `--domain "company.com"` CLI args; `GITHUB_TOKEN` from `.env`
- Produces: `.tmp/github/{domain}.json` — `{domain, fetched_at, found, org, public_repos, top_repos, primary_languages, last_activity}`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_fetch_github_presence.py`:

```python
from unittest.mock import MagicMock

from tools.fetch_github_presence import (
    extract_domain,
    find_github_link_in_html,
    format_repo,
    get_primary_languages,
)


def test_extract_domain():
    assert extract_domain("https://linear.app") == "linear.app"


def test_find_github_link_in_html_finds_org():
    html = '<a href="https://github.com/linearapp">GitHub</a>'
    assert find_github_link_in_html(html) == "linearapp"


def test_find_github_link_in_html_returns_none_when_absent():
    html = "<a href='https://twitter.com/linear'>Twitter</a>"
    assert find_github_link_in_html(html) is None


def test_find_github_link_skips_generic_github_root():
    html = '<a href="https://github.com">GitHub</a>'
    assert find_github_link_in_html(html) is None


def test_format_repo():
    mock_repo = MagicMock()
    mock_repo.name = "linear-api"
    mock_repo.description = "The Linear API client"
    mock_repo.stargazers_count = 512
    mock_repo.language = "TypeScript"
    mock_repo.pushed_at.isoformat.return_value = "2026-07-01T00:00:00"
    result = format_repo(mock_repo)
    assert result == {
        "name": "linear-api",
        "description": "The Linear API client",
        "stars": 512,
        "language": "TypeScript",
        "last_push": "2026-07-01T00:00:00",
    }


def test_get_primary_languages_sorts_by_count():
    mock_repos = [MagicMock(language=lang) for lang in ["TypeScript", "TypeScript", "Python", "Go", "TypeScript"]]
    result = get_primary_languages(mock_repos)
    assert result[0] == "TypeScript"
    assert "Python" in result
    assert "Go" in result


def test_get_primary_languages_excludes_none():
    mock_repos = [MagicMock(language=None), MagicMock(language="Rust")]
    result = get_primary_languages(mock_repos)
    assert result == ["Rust"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_fetch_github_presence.py -v
```

Expected: `ModuleNotFoundError: No module named 'tools.fetch_github_presence'`

- [ ] **Step 3: Implement `tools/fetch_github_presence.py`**

```python
#!/usr/bin/env python3
"""Find a competitor's open-source footprint on GitHub."""

import argparse
import json
import os
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv
from github import Github, GithubException

load_dotenv()

TMP_DIR = Path(".tmp")
GITHUB_DIR = TMP_DIR / "github"

GITHUB_LINK_PATTERN = re.compile(r'https?://github\.com/([^/">\s]+)', re.IGNORECASE)
SKIP_HANDLES = {"", "features", "pricing", "about", "login", "join", "marketplace", "explore"}


def extract_domain(url: str) -> str:
    parsed = urlparse(url if url.startswith("http") else f"https://{url}")
    host = parsed.netloc
    parts = host.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def find_github_link_in_html(html: str) -> str | None:
    for match in GITHUB_LINK_PATTERN.finditer(html):
        handle = match.group(1).rstrip("/")
        if handle and "/" not in handle and handle.lower() not in SKIP_HANDLES:
            return handle
    return None


def format_repo(repo) -> dict:
    return {
        "name": repo.name,
        "description": repo.description,
        "stars": repo.stargazers_count,
        "language": repo.language,
        "last_push": repo.pushed_at.isoformat(),
    }


def get_primary_languages(repos: list) -> list[str]:
    langs = [r.language for r in repos if r.language]
    return [lang for lang, _ in Counter(langs).most_common()]


def fetch(company: str, domain: str) -> dict:
    token = os.getenv("GITHUB_TOKEN")
    g = Github(token) if token else Github()

    result: dict = {
        "domain": domain,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "found": False,
        "org": None,
        "public_repos": 0,
        "top_repos": [],
        "primary_languages": [],
        "last_activity": None,
    }

    org_login = None

    try:
        resp = requests.get(f"https://{domain}", timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        org_login = find_github_link_in_html(resp.text)
    except Exception:
        pass

    if not org_login:
        try:
            users = g.search_users(f"{company} type:org")
            for user in users:
                if any(kw in user.login.lower() for kw in company.lower().split()):
                    org_login = user.login
                    break
        except GithubException:
            pass

    if not org_login:
        return result

    try:
        org = g.get_organization(org_login)
        repos = sorted(org.get_repos(), key=lambda r: r.stargazers_count, reverse=True)
        top_repos = [format_repo(r) for r in repos[:10]]
        result.update({
            "found": True,
            "org": org_login,
            "public_repos": org.public_repos,
            "top_repos": top_repos,
            "primary_languages": get_primary_languages(list(repos)),
            "last_activity": top_repos[0]["last_push"] if top_repos else None,
        })
    except GithubException:
        pass

    return result


def log_error(domain: str, tool: str, message: str) -> None:
    errors_file = TMP_DIR / "errors.json"
    errors = json.loads(errors_file.read_text()) if errors_file.exists() else []
    errors.append({
        "domain": domain,
        "tool": tool,
        "error": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    errors_file.write_text(json.dumps(errors, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch GitHub presence for a competitor.")
    parser.add_argument("--company", required=True, help="Company name")
    parser.add_argument("--domain", required=True, help="Company domain (e.g. linear.app)")
    args = parser.parse_args()

    TMP_DIR.mkdir(exist_ok=True)
    GITHUB_DIR.mkdir(exist_ok=True)

    try:
        data = fetch(args.company, args.domain)
        output = GITHUB_DIR / f"{args.domain}.json"
        output.write_text(json.dumps(data, indent=2))
        print(f"GitHub data for {args.domain} → {output}")
        if data["found"]:
            print(f"  Org: {data['org']} | Repos: {data['public_repos']} | Languages: {', '.join(data['primary_languages'])}")
        else:
            print("  No GitHub presence found")
    except Exception as e:
        log_error(args.domain, "fetch_github_presence", str(e))
        raise


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_fetch_github_presence.py -v
```

Expected: all 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add tools/fetch_github_presence.py tests/test_fetch_github_presence.py
git commit -m "feat: add fetch_github_presence tool using PyGithub"
```

---

### Task 6: analyze_seo.py

**Files:**
- Create: `tools/analyze_seo.py`
- Create: `tests/test_analyze_seo.py`

**Interfaces:**
- Consumes: `--domain "company.com"` CLI arg; reads `.tmp/scraped/{domain}.json` (requires `raw_html` field written by `scrape_competitor.py`)
- Produces: `.tmp/seo/{domain}.json` — `{domain, analyzed_at, title, meta_description, canonical, headings, top_keywords, links, schema_types, og_complete}`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_analyze_seo.py`:

```python
from bs4 import BeautifulSoup

from tools.analyze_seo import (
    check_og_complete,
    count_keywords,
    count_links,
    extract_headings,
    extract_schema_types,
    extract_title,
)

FULL_HTML = """
<html>
<head>
  <title>Writesonic — AI Writing Tool</title>
  <meta name="description" content="Write better content faster with AI">
  <link rel="canonical" href="https://writesonic.com">
  <meta property="og:title" content="Writesonic">
  <meta property="og:description" content="AI writing assistant">
  <meta property="og:image" content="https://writesonic.com/og.png">
  <script type="application/ld+json">{"@type": "Organization"}</script>
</head>
<body>
  <h1>AI Writing Tool</h1>
  <h2>Features</h2>
  <h2>Pricing</h2>
  <h3>Blog</h3>
  <p>Write content faster with our AI writing assistant tool for your business</p>
  <a href="/pricing">Pricing</a>
  <a href="/features">Features</a>
  <a href="https://example.com">External</a>
</body>
</html>
"""


def test_extract_title():
    soup = BeautifulSoup(FULL_HTML, "lxml")
    assert extract_title(soup) == "Writesonic — AI Writing Tool"


def test_extract_headings_h1():
    soup = BeautifulSoup(FULL_HTML, "lxml")
    headings = extract_headings(soup)
    assert headings["h1"] == ["AI Writing Tool"]


def test_extract_headings_h2_count():
    soup = BeautifulSoup(FULL_HTML, "lxml")
    assert len(extract_headings(soup)["h2"]) == 2


def test_extract_headings_h3():
    soup = BeautifulSoup(FULL_HTML, "lxml")
    assert extract_headings(soup)["h3"] == ["Blog"]


def test_count_keywords_top_terms():
    text = "write writing write content content faster AI AI AI tool"
    result = count_keywords(text, top_n=3)
    terms = [r["term"] for r in result]
    assert "ai" in terms
    assert len(result) == 3


def test_count_keywords_excludes_stopwords():
    text = "the best writing tool for the content team"
    result = count_keywords(text, top_n=10)
    terms = [r["term"] for r in result]
    assert "the" not in terms
    assert "for" not in terms


def test_count_links():
    soup = BeautifulSoup(FULL_HTML, "lxml")
    result = count_links(soup, "writesonic.com")
    assert result["internal"] == 2
    assert result["external"] == 1


def test_extract_schema_types():
    soup = BeautifulSoup(FULL_HTML, "lxml")
    assert "Organization" in extract_schema_types(soup)


def test_check_og_complete_true():
    soup = BeautifulSoup(FULL_HTML, "lxml")
    assert check_og_complete(soup) is True


def test_check_og_complete_false_when_missing_image():
    html = """<html><head>
      <meta property="og:title" content="X">
      <meta property="og:description" content="Y">
    </head></html>"""
    soup = BeautifulSoup(html, "lxml")
    assert check_og_complete(soup) is False
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_analyze_seo.py -v
```

Expected: `ModuleNotFoundError: No module named 'tools.analyze_seo'`

- [ ] **Step 3: Implement `tools/analyze_seo.py`**

```python
#!/usr/bin/env python3
"""Extract SEO signals from already-scraped HTML — no additional network requests."""

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

TMP_DIR = Path(".tmp")
SEO_DIR = TMP_DIR / "seo"
SCRAPED_DIR = TMP_DIR / "scraped"

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "up", "about", "into", "through", "is",
    "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "will", "would", "could", "should", "may",
    "might", "shall", "can", "it", "its", "this", "that", "these",
    "those", "i", "we", "you", "he", "she", "they", "me", "us", "him",
    "her", "them", "my", "our", "your", "his", "their", "what", "which",
    "who", "not", "no", "so", "if", "as", "than", "then", "now", "just",
    "all", "more", "new", "get", "use", "make", "also",
}


def extract_title(soup: BeautifulSoup) -> str:
    tag = soup.find("title")
    return tag.get_text(strip=True) if tag else ""


def extract_headings(soup: BeautifulSoup) -> dict:
    return {
        level: [h.get_text(strip=True) for h in soup.find_all(level)]
        for level in ("h1", "h2", "h3")
    }


def count_keywords(text: str, top_n: int = 20) -> list[dict]:
    words = re.findall(r"\b[a-z]{3,}\b", text.lower())
    filtered = [w for w in words if w not in STOPWORDS]
    return [{"term": term, "count": count} for term, count in Counter(filtered).most_common(top_n)]


def count_links(soup: BeautifulSoup, base_domain: str) -> dict:
    internal = external = 0
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("http"):
            domain = urlparse(href).netloc
            if base_domain in domain:
                internal += 1
            else:
                external += 1
        elif href.startswith("/"):
            internal += 1
    return {"internal": internal, "external": external}


def extract_schema_types(soup: BeautifulSoup) -> list[str]:
    types = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            if isinstance(data, dict) and "@type" in data:
                types.append(data["@type"])
            elif isinstance(data, list):
                types.extend(item.get("@type", "") for item in data if "@type" in item)
        except (json.JSONDecodeError, TypeError):
            pass
    return [t for t in types if t]


def check_og_complete(soup: BeautifulSoup) -> bool:
    required = ("og:title", "og:description", "og:image")
    return all(soup.find("meta", property=prop) for prop in required)


def analyze(domain: str) -> dict:
    scrape_file = SCRAPED_DIR / f"{domain}.json"
    scrape_data = json.loads(scrape_file.read_text())
    html = scrape_data.get("raw_html", "")
    soup = BeautifulSoup(html, "lxml")
    body_text = soup.get_text(separator=" ", strip=True)

    canonical = ""
    canon_tag = soup.find("link", rel="canonical")
    if canon_tag:
        canonical = canon_tag.get("href", "")

    return {
        "domain": domain,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "title": extract_title(soup),
        "meta_description": scrape_data.get("homepage", {}).get("meta_description", ""),
        "canonical": canonical,
        "headings": extract_headings(soup),
        "top_keywords": count_keywords(body_text),
        "links": count_links(soup, domain),
        "schema_types": extract_schema_types(soup),
        "og_complete": check_og_complete(soup),
    }


def log_error(domain: str, tool: str, message: str) -> None:
    errors_file = TMP_DIR / "errors.json"
    errors = json.loads(errors_file.read_text()) if errors_file.exists() else []
    errors.append({
        "domain": domain,
        "tool": tool,
        "error": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    errors_file.write_text(json.dumps(errors, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze SEO signals for a scraped competitor.")
    parser.add_argument("--domain", required=True, help="Competitor domain (e.g. writesonic.com)")
    args = parser.parse_args()

    TMP_DIR.mkdir(exist_ok=True)
    SEO_DIR.mkdir(exist_ok=True)

    try:
        data = analyze(args.domain)
        output = SEO_DIR / f"{args.domain}.json"
        output.write_text(json.dumps(data, indent=2))
        print(f"SEO analysis for {args.domain} → {output}")
        print(f"  Title: {data['title']}")
        print(f"  Top keywords: {', '.join(k['term'] for k in data['top_keywords'][:5])}")
    except Exception as e:
        log_error(args.domain, "analyze_seo", str(e))
        raise


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_analyze_seo.py -v
```

Expected: all 10 tests PASS

- [ ] **Step 5: Commit**

```bash
git add tools/analyze_seo.py tests/test_analyze_seo.py
git commit -m "feat: add analyze_seo tool — extracts keywords, headings, schema, OG"
```

---

### Task 7: export_to_sheets.py

**Files:**
- Create: `tools/export_to_sheets.py`
- Create: `tests/test_export_to_sheets.py`

**Interfaces:**
- Consumes: all `.tmp/{scraped,techstack,github,seo}/{domain}.json` files (joined by domain filename)
- Produces: Google Sheet — "Master" tab + one tab per competitor domain

- [ ] **Step 1: Write the failing tests**

Create `tests/test_export_to_sheets.py`:

```python
from tools.export_to_sheets import (
    MASTER_HEADERS,
    build_competitor_detail_rows,
    build_master_row,
    load_competitor_data,
)

SAMPLE_DATA = {
    "domain": "notion.so",
    "scraped": {
        "url": "https://notion.so",
        "homepage": {
            "hero_text": "The all-in-one workspace",
            "meta_description": "Notion is a...",
            "cta_text": "Get started free",
            "og_title": "Notion",
            "og_description": "",
        },
        "pricing": {
            "found": True,
            "tiers": [
                {"name": "Free", "price": "$0", "features": ["Unlimited pages"]},
                {"name": "Plus", "price": "$8/mo", "features": ["Unlimited blocks"]},
            ],
        },
        "features": {"found": True, "items": [{"heading": "Notes", "description": "Take notes"}, {"heading": "Tasks", "description": "Manage tasks"}]},
        "blog": {"found": True, "posts": [{"title": "What is Notion?", "date": "2026-07-01", "summary": "..."}]},
    },
    "techstack": {
        "stack": {
            "frontend": ["React", "Next.js"], "analytics": ["Amplitude"],
            "cdn": ["Cloudflare"], "payments": ["Stripe"], "cms": [],
            "hosting": ["Vercel"], "email": ["Google Workspace"],
            "support": ["Intercom"], "other": [],
        }
    },
    "github": {
        "found": True, "org": "makenotion", "public_repos": 12,
        "top_repos": [{"name": "notion-sdk-js", "stars": 5100, "language": "TypeScript", "description": "Official SDK"}],
        "primary_languages": ["TypeScript", "JavaScript"],
    },
    "seo": {
        "title": "Notion – The all-in-one workspace",
        "top_keywords": [{"term": "notion", "count": 42}, {"term": "workspace", "count": 18}],
        "og_complete": True,
    },
}


def test_master_headers_has_expected_count():
    assert len(MASTER_HEADERS) == 17


def test_build_master_row_length_matches_headers():
    row = build_master_row(SAMPLE_DATA)
    assert len(row) == len(MASTER_HEADERS)


def test_build_master_row_includes_domain():
    row = build_master_row(SAMPLE_DATA)
    assert "notion.so" in row


def test_build_master_row_pricing_summary_includes_tier_name():
    row = build_master_row(SAMPLE_DATA)
    row_str = " ".join(str(v) for v in row)
    assert "Free" in row_str


def test_build_master_row_github_stars():
    row = build_master_row(SAMPLE_DATA)
    assert 5100 in row


def test_build_competitor_detail_rows_has_pricing_section():
    rows = build_competitor_detail_rows(SAMPLE_DATA)
    headings = [str(r[0]).upper() for r in rows if r]
    assert any("PRICING" in h for h in headings)


def test_build_competitor_detail_rows_has_tech_stack_section():
    rows = build_competitor_detail_rows(SAMPLE_DATA)
    headings = [str(r[0]).upper() for r in rows if r]
    assert any("TECH STACK" in h for h in headings)


def test_build_competitor_detail_rows_has_github_section():
    rows = build_competitor_detail_rows(SAMPLE_DATA)
    headings = [str(r[0]).upper() for r in rows if r]
    assert any("GITHUB" in h for h in headings)


def test_build_competitor_detail_rows_has_seo_section():
    rows = build_competitor_detail_rows(SAMPLE_DATA)
    headings = [str(r[0]).upper() for r in rows if r]
    assert any("SEO" in h for h in headings)


def test_load_competitor_data_returns_empty_for_missing_dir(tmp_path):
    result = load_competitor_data(str(tmp_path))
    assert result == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_export_to_sheets.py -v
```

Expected: `ModuleNotFoundError: No module named 'tools.export_to_sheets'`

- [ ] **Step 3: Implement `tools/export_to_sheets.py`**

```python
#!/usr/bin/env python3
"""Export all competitor research data to Google Sheets."""

import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

load_dotenv()

TMP_DIR = Path(".tmp")
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

MASTER_HEADERS = [
    "Domain", "URL", "Hero Text", "Pricing Summary", "# Pricing Tiers",
    "# Features", "Blog Active", "Frontend Stack", "Analytics", "CDN",
    "Payments", "Hosting", "GitHub Org", "GitHub Stars (top repo)",
    "Primary Languages", "Top Keywords", "OG Complete",
]


def load_competitor_data(tmp_dir: str = ".tmp") -> list[dict]:
    base = Path(tmp_dir)
    scraped_dir = base / "scraped"
    if not scraped_dir.exists():
        return []

    competitors = []
    for scraped_file in sorted(scraped_dir.glob("*.json")):
        domain = scraped_file.stem
        entry: dict = {"domain": domain, "scraped": {}, "techstack": {}, "github": {}, "seo": {}}
        entry["scraped"] = json.loads(scraped_file.read_text())
        for subdir in ("techstack", "github", "seo"):
            f = base / subdir / f"{domain}.json"
            if f.exists():
                entry[subdir] = json.loads(f.read_text())
        competitors.append(entry)
    return competitors


def build_master_row(data: dict) -> list:
    scraped = data.get("scraped", {})
    techstack = data.get("techstack", {}).get("stack", {})
    github = data.get("github", {})
    seo = data.get("seo", {})

    tiers = scraped.get("pricing", {}).get("tiers", [])
    pricing_summary = "; ".join(f"{t['name']} {t['price']}" for t in tiers) if tiers else "Not found"

    top_repo_stars = 0
    if github.get("top_repos"):
        top_repo_stars = github["top_repos"][0].get("stars", 0)

    top_keywords = ", ".join(k["term"] for k in seo.get("top_keywords", [])[:5])

    return [
        data.get("domain", ""),
        scraped.get("url", ""),
        scraped.get("homepage", {}).get("hero_text", ""),
        pricing_summary,
        len(tiers),
        len(scraped.get("features", {}).get("items", [])),
        "Yes" if scraped.get("blog", {}).get("found") else "No",
        ", ".join(techstack.get("frontend", [])),
        ", ".join(techstack.get("analytics", [])),
        ", ".join(techstack.get("cdn", [])),
        ", ".join(techstack.get("payments", [])),
        ", ".join(techstack.get("hosting", [])),
        github.get("org", ""),
        top_repo_stars,
        ", ".join(github.get("primary_languages", [])),
        top_keywords,
        "Yes" if seo.get("og_complete") else "No",
    ]


def build_competitor_detail_rows(data: dict) -> list[list]:
    scraped = data.get("scraped", {})
    techstack = data.get("techstack", {}).get("stack", {})
    github = data.get("github", {})
    seo = data.get("seo", {})

    rows: list[list] = []

    rows.append(["=== OVERVIEW ==="])
    rows.append(["Hero", scraped.get("homepage", {}).get("hero_text", "")])
    rows.append(["CTA", scraped.get("homepage", {}).get("cta_text", "")])
    rows.append(["Meta Description", scraped.get("homepage", {}).get("meta_description", "")])
    rows.append([])

    rows.append(["=== PRICING ==="])
    for tier in scraped.get("pricing", {}).get("tiers", []):
        rows.append([tier.get("name", ""), tier.get("price", ""), ", ".join(tier.get("features", []))])
    if not scraped.get("pricing", {}).get("tiers"):
        rows.append(["No pricing data found"])
    rows.append([])

    rows.append(["=== BLOG (latest posts) ==="])
    for post in scraped.get("blog", {}).get("posts", []):
        rows.append([post.get("title", ""), post.get("date", ""), post.get("summary", "")])
    rows.append([])

    rows.append(["=== TECH STACK ==="])
    for category, techs in techstack.items():
        if techs:
            rows.append([category.title(), ", ".join(techs)])
    rows.append([])

    rows.append(["=== GITHUB ==="])
    rows.append(["Org", github.get("org", "Not found")])
    rows.append(["Public Repos", github.get("public_repos", 0)])
    rows.append(["Languages", ", ".join(github.get("primary_languages", []))])
    for repo in github.get("top_repos", []):
        rows.append([repo.get("name", ""), f"★ {repo.get('stars', 0)}", repo.get("language", ""), repo.get("description", "")])
    rows.append([])

    rows.append(["=== SEO ==="])
    rows.append(["Title", seo.get("title", "")])
    rows.append(["OG Complete", "Yes" if seo.get("og_complete") else "No"])
    rows.append(["Top Keywords", ", ".join(k["term"] for k in seo.get("top_keywords", [])[:10])])

    return rows


def get_sheets_service():
    creds = None
    if Path("token.json").exists():
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        Path("token.json").write_text(creds.to_json())
    return build("sheets", "v4", credentials=creds)


def ensure_sheets_exist(service, sheet_id: str, sheet_names: list[str]) -> None:
    meta = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
    existing = {s["properties"]["title"] for s in meta["sheets"]}
    requests_body = [
        {"addSheet": {"properties": {"title": name}}}
        for name in sheet_names
        if name not in existing
    ]
    if requests_body:
        service.spreadsheets().batchUpdate(
            spreadsheetId=sheet_id, body={"requests": requests_body}
        ).execute()


def clear_and_write(service, sheet_id: str, sheet_name: str, rows: list[list]) -> None:
    service.spreadsheets().values().clear(
        spreadsheetId=sheet_id, range=f"'{sheet_name}'!A1:ZZ"
    ).execute()
    service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=f"'{sheet_name}'!A1",
        valueInputOption="RAW",
        body={"values": rows},
    ).execute()


def export(sheet_id: str | None = None) -> str:
    service = get_sheets_service()
    competitors = load_competitor_data()

    if not sheet_id:
        sheet_id = os.getenv("GOOGLE_SHEET_ID") or None

    if not sheet_id:
        result = service.spreadsheets().create(
            body={"properties": {"title": "Competitor Research"}}
        ).execute()
        sheet_id = result["spreadsheetId"]
        print(f"Created new sheet: {sheet_id}")

    sheet_names = ["Master"] + [c["domain"] for c in competitors]
    ensure_sheets_exist(service, sheet_id, sheet_names)

    master_rows = [MASTER_HEADERS] + [build_master_row(c) for c in competitors]
    clear_and_write(service, sheet_id, "Master", master_rows)
    print(f"Written Master tab ({len(competitors)} competitors)")

    for competitor in competitors:
        detail_rows = build_competitor_detail_rows(competitor)
        clear_and_write(service, sheet_id, competitor["domain"], detail_rows)
        print(f"  Written: {competitor['domain']}")

    return f"https://docs.google.com/spreadsheets/d/{sheet_id}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Export competitor research to Google Sheets.")
    parser.add_argument("--sheet-id", help="Existing Google Sheet ID (creates new if omitted)")
    args = parser.parse_args()

    url = export(sheet_id=args.sheet_id)
    print(f"\nSheet: {url}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_export_to_sheets.py -v
```

Expected: all 10 tests PASS

- [ ] **Step 5: Commit**

```bash
git add tools/export_to_sheets.py tests/test_export_to_sheets.py
git commit -m "feat: add export_to_sheets tool — Master tab + per-competitor detail tabs"
```

---

### Task 8: Workflow files

**Files:**
- Create: `workflows/research_competitors.md`
- Create: `workflows/scrape_website.md`
- Create: `workflows/export_to_google_sheets.md`

- [ ] **Step 1: Write `workflows/research_competitors.md`**

```markdown
# Workflow: Research Competitors

## Objective
Discover and research competitors for a given keyword or seed URL, then export all findings to Google Sheets.

## Required Inputs
- At least one of:
  - `--query`: a keyword or product category (e.g. "AI writing tools")
  - `--url`: a known competitor URL to discover peers from (e.g. "https://writesonic.com")
- `GOOGLE_SHEET_ID` in `.env` (optional — a new sheet will be created if absent)

## Steps

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

### 3. Export to Google Sheets
```bash
python tools/export_to_sheets.py [--sheet-id "YOUR_SHEET_ID"]
```

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
| No GitHub presence | `github.found = false`; GitHub columns left blank in Sheet |
| Rate limited (HTTP 429) | Wait 60 seconds, retry once; if still failing, skip and log |
| Cookie consent wall | Scraper auto-clicks Accept; if blocked, some data may be missing |
```

- [ ] **Step 2: Write `workflows/scrape_website.md`**

```markdown
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
```

- [ ] **Step 3: Write `workflows/export_to_google_sheets.md`**

```markdown
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
```

- [ ] **Step 4: Run the full test suite**

```bash
pytest tests/ -v
```

Expected: all tests across all six test files PASS

- [ ] **Step 5: Commit**

```bash
git add workflows/research_competitors.md workflows/scrape_website.md workflows/export_to_google_sheets.md
git commit -m "docs: add three workflow SOPs — research, scrape, and Sheets export"
```

---

## Self-Review

**Spec coverage:**
- ✅ `discover_competitors.py` — keyword + URL input, DuckDuckGo, dedup, noise filtering
- ✅ `scrape_competitor.py` — Playwright, homepage/pricing/features/blog extraction, requests fallback, `raw_html` field
- ✅ `detect_tech_stack.py` — Wappalyzer, DNS MX, path probes, category mapping
- ✅ `fetch_github_presence.py` — org link detection in HTML, GitHub search fallback, repo/language data
- ✅ `analyze_seo.py` — reads `raw_html` from scrape output, no re-fetch, keywords/headings/schema/OG
- ✅ `export_to_sheets.py` — Master tab (17 columns) + per-competitor tabs, idempotent, auto-creates sheet
- ✅ Error handling — all tools log to `.tmp/errors.json`, write partial data on failure
- ✅ `workflows/research_competitors.md` — end-to-end SOP with edge case table
- ✅ `workflows/scrape_website.md` — scraping mechanics, fallback, `raw_html` note
- ✅ `workflows/export_to_google_sheets.md` — one-time setup + runtime SOP + column extension guide
- ✅ `.env` keys — `GITHUB_TOKEN` and `GOOGLE_SHEET_ID` in `.env.example`
- ✅ No paid APIs

**Type consistency:**
- `extract_domain()` and `log_error()` duplicated per-file (per Global Constraints)
- `MASTER_HEADERS` has 17 entries; `build_master_row()` returns exactly 17 values — verified by counting
- `analyze_seo.py` reads `.tmp/scraped/{domain}.json["raw_html"]` — written by `scrape_competitor.py` at that exact key
- `export_to_sheets.py` joins by `{domain}.json` stem — consistent across all four `.tmp/` subdirs
