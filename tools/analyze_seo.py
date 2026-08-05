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
    words = re.findall(r"\b[a-z]{2,}\b", text.lower())
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
