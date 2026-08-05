#!/usr/bin/env python3
"""Export all competitor research data to Google Sheets."""

import argparse
import json
import os
from datetime import datetime, timezone
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


def log_error(tool: str, message: str) -> None:
    errors_file = TMP_DIR / "errors.json"
    errors = json.loads(errors_file.read_text()) if errors_file.exists() else []
    errors.append({
        "domain": "",
        "tool": tool,
        "error": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    errors_file.write_text(json.dumps(errors, indent=2))


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

    try:
        url = export(sheet_id=args.sheet_id)
        print(f"\nSheet: {url}")
    except Exception as e:
        log_error("export_to_sheets", str(e))
        raise


if __name__ == "__main__":
    main()
