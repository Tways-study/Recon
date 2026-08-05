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
        "last_push": repo.pushed_at.isoformat() if repo.pushed_at else None,
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
