#!/usr/bin/env python3
"""Export all competitor research data to a plain markdown report."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


TMP_DIR = Path(".tmp")
DEFAULT_OUTPUT = TMP_DIR / "competitor_analysis.md"


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


def md_table(headers: list[str], rows: list[list]) -> str:
    col_widths = [len(h) for h in headers]
    str_rows = [[str(cell) for cell in row] for row in rows]
    for row in str_rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(cell))

    def fmt_row(cells: list[str]) -> str:
        return "| " + " | ".join(c.ljust(col_widths[i]) for i, c in enumerate(cells)) + " |"

    sep = "| " + " | ".join("-" * w for w in col_widths) + " |"
    lines = [fmt_row(headers), sep] + [fmt_row(r) for r in str_rows]
    return "\n".join(lines)


def build_master_row(data: dict) -> list:
    scraped = data.get("scraped", {})
    techstack = data.get("techstack", {}).get("stack", {})
    github = data.get("github", {})
    seo = data.get("seo", {})

    tiers = scraped.get("pricing", {}).get("tiers", [])
    pricing_summary = "; ".join(f"{t['name']} {t['price']}" for t in tiers) if tiers else "Not found"

    top_repo_stars = ""
    if github.get("top_repos"):
        top_repo_stars = str(github["top_repos"][0].get("stars", 0))

    top_keywords = ", ".join(k["term"] for k in seo.get("top_keywords", [])[:5])

    return [
        data.get("domain", ""),
        scraped.get("homepage", {}).get("hero_text", "")[:80],
        pricing_summary,
        str(len(tiers)),
        str(len(scraped.get("features", {}).get("items", []))),
        "Yes" if scraped.get("blog", {}).get("found") else "No",
        ", ".join(techstack.get("frontend", [])),
        ", ".join(techstack.get("analytics", [])),
        github.get("org", ""),
        top_repo_stars,
        top_keywords,
        "Yes" if seo.get("og_complete") else "No",
    ]


MASTER_HEADERS = [
    "Domain", "Hero Text", "Pricing Summary", "Tiers", "Features",
    "Blog", "Frontend", "Analytics", "GitHub Org", "Top Repo Stars",
    "Top Keywords", "OG Complete",
]


def build_competitor_section(data: dict) -> str:
    domain = data.get("domain", "")
    scraped = data.get("scraped", {})
    techstack = data.get("techstack", {}).get("stack", {})
    github = data.get("github", {})
    seo = data.get("seo", {})
    homepage = scraped.get("homepage", {})

    lines: list[str] = []
    lines.append(f"## {domain}")
    lines.append("")

    # Overview
    lines.append("### Overview")
    lines.append("")
    if homepage.get("hero_text"):
        lines.append(f"**Hero:** {homepage['hero_text']}")
    if homepage.get("cta_text"):
        lines.append(f"**CTA:** {homepage['cta_text']}")
    if homepage.get("meta_description"):
        lines.append(f"**Meta:** {homepage['meta_description']}")
    lines.append("")

    # Pricing
    lines.append("### Pricing")
    lines.append("")
    tiers = scraped.get("pricing", {}).get("tiers", [])
    if tiers:
        tier_headers = ["Plan", "Price", "Features"]
        tier_rows = [
            [t.get("name", ""), t.get("price", ""), ", ".join(t.get("features", [])[:5])]
            for t in tiers
        ]
        lines.append(md_table(tier_headers, tier_rows))
    else:
        lines.append("No pricing data found.")
    lines.append("")

    # Blog
    lines.append("### Blog")
    lines.append("")
    posts = scraped.get("blog", {}).get("posts", [])
    if posts:
        post_headers = ["Title", "Date", "Summary"]
        post_rows = [[p.get("title", ""), p.get("date", ""), p.get("summary", "")] for p in posts]
        lines.append(md_table(post_headers, post_rows))
    else:
        lines.append("No blog posts found." if not scraped.get("blog", {}).get("found") else "Blog found but no posts extracted.")
    lines.append("")

    # Tech Stack
    lines.append("### Tech Stack")
    lines.append("")
    if techstack:
        stack_rows = [[cat.title(), ", ".join(techs)] for cat, techs in techstack.items() if techs]
        if stack_rows:
            lines.append(md_table(["Category", "Technologies"], stack_rows))
        else:
            lines.append("No tech stack detected.")
    else:
        lines.append("No tech stack detected.")
    lines.append("")

    # GitHub
    lines.append("### GitHub")
    lines.append("")
    if github.get("found"):
        lines.append(f"**Org:** {github.get('org', '')}")
        lines.append(f"**Public Repos:** {github.get('public_repos', 0)}")
        languages = github.get("primary_languages", [])
        if languages:
            lines.append(f"**Languages:** {', '.join(languages)}")
        top_repos = github.get("top_repos", [])
        if top_repos:
            lines.append("")
            repo_rows = [
                [r.get("name", ""), f"★ {r.get('stars', 0)}", r.get("language", ""), r.get("description", "")[:60]]
                for r in top_repos
            ]
            lines.append(md_table(["Repo", "Stars", "Language", "Description"], repo_rows))
    else:
        lines.append("No GitHub presence found.")
    lines.append("")

    # SEO
    lines.append("### SEO")
    lines.append("")
    if seo:
        if seo.get("title"):
            lines.append(f"**Title:** {seo['title']}")
        lines.append(f"**OG Complete:** {'Yes' if seo.get('og_complete') else 'No'}")
        keywords = seo.get("top_keywords", [])
        if keywords:
            lines.append(f"**Top Keywords:** {', '.join(k['term'] for k in keywords[:10])}")
        headings = seo.get("headings", [])
        if headings:
            lines.append("")
            lines.append("**Headings:**")
            for h in headings[:8]:
                tag = h.get("tag", "h2")
                indent = "  " * (int(tag[1]) - 1) if tag[1:].isdigit() else ""
                lines.append(f"{indent}- {h.get('text', '')}")
    else:
        lines.append("No SEO data found.")
    lines.append("")

    return "\n".join(lines)


def export(output_path: Path = DEFAULT_OUTPUT) -> Path:
    competitors = load_competitor_data()
    if not competitors:
        print("No competitor data found in .tmp/scraped/")
        return output_path

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines: list[str] = []

    lines.append("# Scout Report")
    lines.append("")
    lines.append(f"Generated: {now}  ")
    lines.append(f"Competitors: {len(competitors)}")
    lines.append("")

    # Master comparison table
    lines.append("## Master Comparison")
    lines.append("")
    master_rows = [build_master_row(c) for c in competitors]
    lines.append(md_table(MASTER_HEADERS, master_rows))
    lines.append("")
    lines.append("---")
    lines.append("")

    # Per-competitor detail sections
    lines.append("## Competitor Details")
    lines.append("")
    for competitor in competitors:
        lines.append(build_competitor_section(competitor))
        lines.append("---")
        lines.append("")

    report = "\n".join(lines)
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Export competitor research to markdown.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output file path")
    args = parser.parse_args()

    output_path = Path(args.output)
    result = export(output_path=output_path)
    print(f"Report written to: {result}")


if __name__ == "__main__":
    main()
