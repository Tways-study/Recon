#!/usr/bin/env python3
"""Discover competitor URLs from a keyword, seed URL, or both."""

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from duckduckgo_search.exceptions import RatelimitException
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
    "bing.com", "google.com", "microsoft.com",
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

    # Page title often has "Company | Category" — the category part is the best query seed
    title_tag = soup.find("title")
    if title_tag:
        title = title_tag.get_text(strip=True)
        for sep in (" | ", " - ", " – ", " — "):
            if sep in title:
                parts = [p.strip() for p in title.split(sep) if p.strip()]
                # Take the longest part that isn't just the company name (heuristic: >15 chars)
                descriptive = [p for p in parts if len(p) > 15]
                if descriptive:
                    return descriptive[0][:60]

    # Meta description — truncate at the first clause boundary to avoid full sentences
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        desc = meta["content"].strip()
        for sep in (",", ".", " for ", " that ", " helping ", " to help "):
            if sep in desc:
                fragment = desc.split(sep)[0].strip()
                if len(fragment) > 10:
                    return fragment[:60]
        return desc[:60]

    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)[:60]

    return extract_domain(url)


def build_queries(base_query: str) -> list[str]:
    return [
        base_query,
        f"{base_query} alternatives",
        f"best {base_query}",
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
        # Only extract a query from the seed page when no explicit query was given
        if not query:
            seed_query = parse_seed_url(resp.text, url)
            base_query = seed_query

    all_results: list[dict] = []
    for i, q in enumerate(build_queries(base_query)):
        if i > 0:
            time.sleep(2)
        try:
            all_results.extend(search_ddg(q))
        except RatelimitException:
            print("  DDG rate limited — try again in a few minutes or use a VPN.")
            break

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
