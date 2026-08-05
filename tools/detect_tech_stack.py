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
