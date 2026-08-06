#!/usr/bin/env python3
"""Full Scout pipeline: discover → scrape → tech stack → GitHub → SEO → export."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from tools.discover_competitors import discover
from tools.scrape_competitor import scrape
from tools.detect_tech_stack import detect
from tools.fetch_github_presence import fetch
from tools.analyze_seo import analyze

load_dotenv()

TMP_DIR = Path(".tmp")
SCRAPED_DIR = TMP_DIR / "scraped"
TECHSTACK_DIR = TMP_DIR / "techstack"
GITHUB_DIR = TMP_DIR / "github"
SEO_DIR = TMP_DIR / "seo"


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


def research_competitor(competitor: dict) -> list[str]:
    """Run all four research tools against one competitor. Returns a list of error strings."""
    domain = competitor["domain"]
    url = competitor["url"]
    name = competitor.get("name", domain)
    errors: list[str] = []

    print(f"  scraping...")
    try:
        data = scrape(url)
        (SCRAPED_DIR / f"{domain}.json").write_text(json.dumps(data, indent=2))
        print(f"  scraped")
    except Exception as e:
        msg = str(e)
        log_error(domain, "scrape_competitor", msg)
        errors.append(f"scrape: {msg[:100]}")
        print(f"  scrape failed: {msg[:100]}")

    print(f"  detecting tech stack...")
    try:
        data = detect(url)
        (TECHSTACK_DIR / f"{domain}.json").write_text(json.dumps(data, indent=2))
        print(f"  tech stack done")
    except Exception as e:
        msg = str(e)
        log_error(domain, "detect_tech_stack", msg)
        errors.append(f"techstack: {msg[:100]}")
        print(f"  tech stack failed: {msg[:100]}")

    print(f"  fetching GitHub presence...")
    try:
        data = fetch(name, domain)
        (GITHUB_DIR / f"{domain}.json").write_text(json.dumps(data, indent=2))
        print(f"  GitHub done")
    except Exception as e:
        msg = str(e)
        log_error(domain, "fetch_github_presence", msg)
        errors.append(f"github: {msg[:100]}")
        print(f"  GitHub failed: {msg[:100]}")

    scrape_file = SCRAPED_DIR / f"{domain}.json"
    if scrape_file.exists():
        print(f"  analyzing SEO...")
        try:
            data = analyze(domain)
            (SEO_DIR / f"{domain}.json").write_text(json.dumps(data, indent=2))
            print(f"  SEO done")
        except Exception as e:
            msg = str(e)
            log_error(domain, "analyze_seo", msg)
            errors.append(f"seo: {msg[:100]}")
            print(f"  SEO failed: {msg[:100]}")
    else:
        errors.append("seo: skipped (no scrape data)")
        print(f"  SEO skipped — no scrape data")

    return errors


def run_export(export_format: str) -> None:
    if export_format == "html":
        from tools.export_to_html import export
        output = export()
        print(f"  Report: {output}")
    elif export_format == "markdown":
        from tools.export_to_markdown import export
        output = export()
        print(f"  Report: {output}")
    elif export_format == "sheets":
        from tools.export_to_sheets import export
        url = export()
        print(f"  Sheet: {url}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scout: discover competitors and export a research report.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  python scout.py --url https://writesonic.com
  python scout.py --query "AI writing tools" --max-competitors 8
  python scout.py --url https://notion.so --export sheets
        """,
    )
    parser.add_argument("--url", help="Seed URL — Scout finds competitors similar to this site")
    parser.add_argument("--query", help="Keyword or product category to search for competitors")
    parser.add_argument("--max-competitors", type=int, default=5, metavar="N",
                        help="Cap on how many competitors to research (default: 5)")
    parser.add_argument("--export", choices=["html", "markdown", "sheets"], default="html",
                        help="Output format (default: html)")
    args = parser.parse_args()

    if not args.url and not args.query:
        parser.error("Provide at least one of --url or --query")

    for d in [TMP_DIR, SCRAPED_DIR, TECHSTACK_DIR, GITHUB_DIR, SEO_DIR]:
        d.mkdir(exist_ok=True)

    # Step 1 — Discover
    print(f"\n[1] Discovering competitors...")
    competitors = discover(query=args.query, url=args.url)
    competitors = competitors[: args.max_competitors]
    (TMP_DIR / "competitors.json").write_text(json.dumps(competitors, indent=2))
    print(f"    Found {len(competitors)} competitors:")
    for c in competitors:
        print(f"    - {c['domain']}")

    # Steps 2-5 — Research each competitor
    fully_done: list[str] = []
    partial: list[tuple[str, list[str]]] = []

    for i, competitor in enumerate(competitors, 1):
        domain = competitor["domain"]
        print(f"\n[{i + 1}/{len(competitors) + 2}] {domain}")
        errors = research_competitor(competitor)
        if errors:
            partial.append((domain, errors))
        else:
            fully_done.append(domain)

    # Final step — Export
    print(f"\n[{len(competitors) + 2}/{len(competitors) + 2}] Exporting ({args.export})...")
    try:
        run_export(args.export)
    except Exception as e:
        print(f"  Export failed: {e}")

    # Summary
    print(f"\n{'=' * 52}")
    print(f"  Scout complete")
    print(f"  Fully researched : {len(fully_done)}  {', '.join(fully_done) or '—'}")
    if partial:
        print(f"  Partial data     : {len(partial)}")
        for domain, errs in partial:
            print(f"    {domain}: {'; '.join(errs)}")
    errors_file = TMP_DIR / "errors.json"
    if errors_file.exists():
        n = len(json.loads(errors_file.read_text()))
        if n:
            print(f"  Errors logged    : {n}  -> .tmp/errors.json")
    print(f"{'=' * 52}\n")


if __name__ == "__main__":
    main()
