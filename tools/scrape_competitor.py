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
