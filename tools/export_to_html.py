#!/usr/bin/env python3
"""Export all competitor research data to a self-contained HTML report."""

import argparse
import html as _html
import json
from datetime import datetime, timezone
from pathlib import Path


TMP_DIR = Path(".tmp")
DEFAULT_OUTPUT = TMP_DIR / "competitor_analysis.html"

# ---------------------------------------------------------------------------
# CSS — dark intelligence-terminal aesthetic
# OKLCH token set:
#   --bg       near-black navy-tint    oklch(12% 0.02 250)
#   --surface  elevated card bg        oklch(17% 0.02 250)
#   --surface-2 table header / nested  oklch(22% 0.025 250)
#   --accent   electric teal           oklch(72% 0.18 195)
#   --accent-dim hover / border tint   oklch(40% 0.10 195)
#   --ink      body text ≥7:1 contrast oklch(93% 0.005 250)
#   --muted    secondary labels        oklch(62% 0.01 250)
#   --border   dividers / borders      oklch(25% 0.03 250)
# ---------------------------------------------------------------------------
CSS_BLOCK = """
:root {
  --bg:         oklch(12% 0.02 250);
  --surface:    oklch(17% 0.02 250);
  --surface-2:  oklch(22% 0.025 250);
  --accent:     oklch(72% 0.18 195);
  --accent-dim: oklch(28% 0.06 195);
  --ink:        oklch(93% 0.005 250);
  --muted:      oklch(62% 0.01 250);
  --border:     oklch(25% 0.03 250);
  --sidebar-w:  220px;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html { scroll-behavior: smooth; }

body {
  font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: var(--bg);
  color: var(--ink);
  display: grid;
  grid-template-columns: var(--sidebar-w) 1fr;
  min-height: 100vh;
  line-height: 1.5;
}

/* ── Sidebar ── */
.sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  overflow-y: auto;
  overflow-x: hidden;
  background: var(--surface);
  border-right: 1px solid var(--border);
  padding: 1.5rem 0 2rem;
  display: flex;
  flex-direction: column;
  scrollbar-width: thin;
  scrollbar-color: var(--border) transparent;
}

.sidebar-logo {
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  color: var(--accent);
  text-transform: uppercase;
  padding: 0 1.25rem 0.35rem;
}

.sidebar-meta {
  font-size: 0.68rem;
  color: var(--muted);
  font-family: ui-monospace, "Cascadia Code", "Fira Code", monospace;
  padding: 0 1.25rem 1.25rem;
  border-bottom: 1px solid var(--border);
  margin-bottom: 0.75rem;
}

.nav-section-label {
  font-size: 0.62rem;
  font-weight: 600;
  color: oklch(45% 0.01 250);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 1rem 1.25rem 0.3rem;
}

.nav-link {
  display: block;
  padding: 0.38rem 1.25rem;
  font-size: 0.78rem;
  color: var(--muted);
  text-decoration: none;
  transition: color 0.12s, background 0.12s;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.nav-link:hover { color: var(--ink); background: var(--surface-2); }

.nav-link.active {
  color: var(--accent);
  background: var(--accent-dim);
}

.nav-link.overview-link {
  font-weight: 600;
  color: var(--ink);
}

/* ── Main content ── */
.content {
  padding: 3rem 2.5rem 5rem;
  max-width: 1140px;
}

/* ── Report header ── */
.report-header {
  margin-bottom: 3.5rem;
  padding-bottom: 1.75rem;
  border-bottom: 1px solid var(--border);
}

.report-header h1 {
  font-size: clamp(1.75rem, 3vw, 2.75rem);
  font-weight: 800;
  letter-spacing: -0.04em;
  line-height: 1.08;
  color: var(--ink);
  text-wrap: balance;
}

.report-header h1 span {
  color: var(--accent);
}

.report-meta {
  display: inline-block;
  margin-top: 0.6rem;
  font-size: 0.75rem;
  font-family: ui-monospace, monospace;
  color: var(--muted);
}

/* ── Section structure ── */
.section-heading {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--ink);
  letter-spacing: -0.025em;
  margin-bottom: 1rem;
  text-wrap: balance;
}

.subsection-label {
  font-size: 0.65rem;
  font-weight: 700;
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-bottom: 0.6rem;
  margin-top: 1.75rem;
  display: block;
}

.subsection-label:first-child { margin-top: 0; }

/* ── Tables ── */
.table-scroll {
  overflow-x: auto;
  border-radius: 8px;
  border: 1px solid var(--border);
  margin-bottom: 0.5rem;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8rem;
}

.data-table thead th {
  background: var(--surface-2);
  color: var(--muted);
  font-size: 0.65rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 0.55rem 0.9rem;
  text-align: left;
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}

.data-table tbody tr { border-bottom: 1px solid var(--border); transition: background 0.1s; }
.data-table tbody tr:last-child { border-bottom: none; }
.data-table tbody tr:hover { background: var(--surface-2); }

.data-table td {
  padding: 0.6rem 0.9rem;
  vertical-align: top;
  color: var(--ink);
}

.data-table td.mono {
  font-family: ui-monospace, monospace;
  font-size: 0.75rem;
}

.data-table td.domain-cell {
  font-family: ui-monospace, monospace;
  font-size: 0.8rem;
  font-weight: 700;
  white-space: nowrap;
}

.data-table td.domain-cell a {
  color: var(--accent);
  text-decoration: none;
}

.data-table td.domain-cell a:hover { text-decoration: underline; }

.data-table td.wrap { white-space: normal; max-width: 220px; word-break: break-word; }

/* ── Badges ── */
.badge {
  display: inline-block;
  padding: 0.15em 0.45em;
  border-radius: 4px;
  font-size: 0.68rem;
  font-family: ui-monospace, monospace;
  font-weight: 600;
}

.badge-yes { background: oklch(20% 0.05 195); color: var(--accent); }
.badge-no  { background: var(--surface-2); color: var(--muted); }

/* ── Master section ── */
#master { margin-bottom: 4.5rem; }

/* ── Competitor sections ── */
.competitor-section {
  margin-bottom: 5rem;
  padding-top: 0.5rem;
}

.competitor-section hr.section-divider {
  border: none;
  border-top: 1px solid var(--border);
  margin: 4.5rem 0 0;
}

.competitor-name {
  font-size: clamp(1.4rem, 2.5vw, 2.1rem);
  font-weight: 800;
  letter-spacing: -0.04em;
  color: var(--ink);
  text-wrap: balance;
  line-height: 1.1;
  margin-bottom: 0.2rem;
}

.competitor-url-line {
  font-family: ui-monospace, monospace;
  font-size: 0.75rem;
  color: var(--muted);
  margin-bottom: 2rem;
  display: block;
}

/* ── Two-column grid for overview + pricing ── */
.top-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}

/* ── Info cards ── */
.info-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 1.25rem;
}

.info-row {
  margin-bottom: 0.9rem;
}

.info-row:last-child { margin-bottom: 0; }

.info-label {
  font-size: 0.64rem;
  font-weight: 700;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  display: block;
  margin-bottom: 0.2rem;
}

.info-value {
  font-size: 0.84rem;
  color: var(--ink);
  line-height: 1.5;
  max-width: 65ch;
}

/* ── Tech stack ── */
.tech-stack-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 1.5rem;
}

.tech-row {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 0.6rem 1.25rem;
  border-bottom: 1px solid var(--border);
}

.tech-row:last-child { border-bottom: none; }

.tech-category {
  font-size: 0.64rem;
  font-weight: 700;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  min-width: 76px;
  flex-shrink: 0;
  padding-top: 0.2rem;
}

.tags { display: flex; flex-wrap: wrap; gap: 0.3rem; }

.tag {
  display: inline-block;
  background: var(--surface-2);
  color: var(--ink);
  font-size: 0.7rem;
  font-family: ui-monospace, monospace;
  padding: 0.18em 0.5em;
  border-radius: 4px;
  border: 1px solid var(--border);
}

/* ── GitHub stats ── */
.github-stats-row {
  display: flex;
  gap: 2.5rem;
  margin-bottom: 1.25rem;
  padding: 1rem 0;
}

.github-stat {
  font-family: ui-monospace, monospace;
  font-size: 0.75rem;
  color: var(--muted);
}

.github-stat .stat-value {
  display: block;
  font-size: 1.35rem;
  font-weight: 700;
  color: var(--ink);
  line-height: 1.1;
  margin-bottom: 0.15rem;
}

.github-stat .stat-value.accent { color: var(--accent); }

/* ── SEO keywords ── */
.keyword-cloud { display: flex; flex-wrap: wrap; gap: 0.3rem; margin-top: 0.4rem; }

.keyword {
  display: inline-flex;
  align-items: baseline;
  gap: 0.25em;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 0.18em 0.55em;
  font-size: 0.71rem;
  font-family: ui-monospace, monospace;
}

.keyword .kw-term { color: var(--ink); }
.keyword .kw-count { color: var(--muted); font-size: 0.65rem; }

/* ── Heading outline ── */
.heading-outline {
  font-family: ui-monospace, monospace;
  font-size: 0.73rem;
  line-height: 1.9;
}

.hline { display: block; color: var(--muted); }
.hline.h1 { color: var(--ink); font-weight: 600; }
.hline.h2 { padding-left: 1.1rem; }
.hline.h3 { padding-left: 2.2rem; color: oklch(50% 0.01 250); }

/* ── Empty states ── */
.not-found {
  font-size: 0.78rem;
  color: var(--muted);
  font-style: italic;
  padding: 0.5rem 0;
  display: block;
}

/* ── Responsive ── */
@media (max-width: 780px) {
  body {
    grid-template-columns: 1fr;
    grid-template-rows: auto 1fr;
  }

  .sidebar {
    position: sticky;
    top: 0;
    height: auto;
    max-height: 56px;
    overflow: hidden;
    flex-direction: row;
    flex-wrap: nowrap;
    align-items: center;
    padding: 0 1rem;
    gap: 0;
    border-right: none;
    border-bottom: 1px solid var(--border);
    z-index: 10;
  }

  .sidebar-logo {
    padding: 0;
    margin-right: 0.75rem;
    flex-shrink: 0;
  }

  .sidebar-meta { display: none; }
  .nav-section-label { display: none; }

  .nav-link {
    padding: 0.35rem 0.55rem;
    border-radius: 4px;
    font-size: 0.72rem;
    flex-shrink: 0;
  }

  .nav-link.overview-link { margin-right: 0.25rem; }

  .content { padding: 1.75rem 1.25rem 4rem; }
}

@media (prefers-reduced-motion: reduce) {
  html { scroll-behavior: auto; }
  *, *::before, *::after { transition: none !important; animation: none !important; }
}
"""

# ---------------------------------------------------------------------------
# JavaScript — IntersectionObserver for sidebar active states
# ---------------------------------------------------------------------------
JS_BLOCK = """
(function () {
  const sections = document.querySelectorAll('section[id]');
  const navLinks = document.querySelectorAll('.nav-link[href^="#"]');
  if (!sections.length || !navLinks.length) return;

  const activate = (id) => {
    navLinks.forEach(link => {
      const active = link.getAttribute('href') === '#' + id;
      link.classList.toggle('active', active);
      if (active) {
        link.scrollIntoView({ block: 'nearest' });
      }
    });
  };

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) activate(entry.target.id);
    });
  }, { rootMargin: '-15% 0px -75% 0px', threshold: 0 });

  sections.forEach(s => observer.observe(s));
})();
"""


# ---------------------------------------------------------------------------
# Data loading (mirrors export_to_markdown.py)
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------
def e(val) -> str:
    """Escape a value for safe HTML output."""
    if val is None:
        return ""
    return _html.escape(str(val))


def render_tag_list(items: list) -> str:
    if not items:
        return '<span class="not-found">None detected</span>'
    return '<div class="tags">' + "".join(f'<span class="tag">{e(i)}</span>' for i in items) + "</div>"


def render_badge(value: bool) -> str:
    if value:
        return '<span class="badge badge-yes">Yes</span>'
    return '<span class="badge badge-no">No</span>'


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------
def render_pricing_section(scraped: dict) -> str:
    pricing = scraped.get("pricing", {})
    tiers = pricing.get("tiers", [])
    if not tiers:
        return '<span class="not-found">No pricing data found.</span>'

    rows = []
    for tier in tiers:
        name = e(tier.get("name", ""))
        price = e(tier.get("price", ""))
        features = tier.get("features", [])
        features_html = "<br>".join(e(f) for f in features[:7])
        rows.append(f'<tr><td class="mono">{name}</td><td class="mono">{price}</td><td class="wrap">{features_html}</td></tr>')

    rows_html = "\n".join(rows)
    return f"""<div class="table-scroll">
  <table class="data-table">
    <thead><tr><th>Plan</th><th>Price</th><th>Features</th></tr></thead>
    <tbody>{rows_html}</tbody>
  </table>
</div>"""


def render_blog_section(scraped: dict) -> str:
    blog = scraped.get("blog", {})
    posts = blog.get("posts", [])
    if not posts:
        return '<span class="not-found">No blog posts found.</span>'

    rows = []
    for post in posts:
        title = e(post.get("title", ""))
        date = e(post.get("date", ""))
        summary = e(post.get("summary", ""))
        rows.append(f'<tr><td class="wrap">{title}</td><td class="mono" style="white-space:nowrap">{date}</td><td class="wrap">{summary}</td></tr>')

    rows_html = "\n".join(rows)
    return f"""<div class="table-scroll">
  <table class="data-table">
    <thead><tr><th>Title</th><th>Date</th><th>Summary</th></tr></thead>
    <tbody>{rows_html}</tbody>
  </table>
</div>"""


def render_tech_stack_section(techstack: dict) -> str:
    stack = techstack.get("stack", {})
    if not stack:
        return '<span class="not-found">No tech stack detected.</span>'

    category_order = ["frontend", "analytics", "cdn", "payments", "cms", "hosting", "email", "support", "other"]
    rows = []
    for cat in category_order:
        techs = stack.get(cat, [])
        if techs:
            tags_html = "".join(f'<span class="tag">{e(t)}</span>' for t in techs)
            rows.append(
                f'<div class="tech-row">'
                f'<span class="tech-category">{e(cat.title())}</span>'
                f'<div class="tags">{tags_html}</div>'
                f"</div>"
            )

    for cat, techs in stack.items():
        if cat not in category_order and techs:
            tags_html = "".join(f'<span class="tag">{e(t)}</span>' for t in techs)
            rows.append(
                f'<div class="tech-row">'
                f'<span class="tech-category">{e(cat.title())}</span>'
                f'<div class="tags">{tags_html}</div>'
                f"</div>"
            )

    if not rows:
        return '<span class="not-found">No tech stack detected.</span>'

    return f'<div class="tech-stack-card">' + "\n".join(rows) + "</div>"


def render_github_section(github: dict) -> str:
    if not github.get("found"):
        return '<span class="not-found">No GitHub presence found.</span>'

    org = e(github.get("org", ""))
    public_repos = e(github.get("public_repos", 0))
    languages = github.get("primary_languages", [])
    lang_tags = "".join(f'<span class="tag">{e(l)}</span>' for l in languages) if languages else ""
    lang_row = f'<div class="github-stat"><span class="stat-value">{lang_tags}</span>Languages</div>' if lang_tags else ""

    stats_html = f"""<div class="github-stats-row">
  <div class="github-stat"><span class="stat-value accent">{org}</span>Org</div>
  <div class="github-stat"><span class="stat-value">{public_repos}</span>Public Repos</div>
  {lang_row}
</div>"""

    top_repos = github.get("top_repos", [])
    if not top_repos:
        return stats_html

    rows = []
    for repo in top_repos:
        name = e(repo.get("name", ""))
        stars = e(repo.get("stars", 0))
        lang = e(repo.get("language", "") or "")
        desc = e(repo.get("description", "") or "")
        last_push = e(repo.get("last_push", "") or "")
        rows.append(
            f'<tr>'
            f'<td class="mono">{name}</td>'
            f'<td class="mono" style="white-space:nowrap">★ {stars}</td>'
            f'<td class="mono">{lang}</td>'
            f'<td class="wrap">{desc}</td>'
            f'<td class="mono" style="white-space:nowrap">{last_push[:10] if last_push else ""}</td>'
            f"</tr>"
        )

    repos_html = f"""<div class="table-scroll">
  <table class="data-table">
    <thead><tr><th>Repo</th><th>Stars</th><th>Language</th><th>Description</th><th>Last Push</th></tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table>
</div>"""

    return stats_html + repos_html


def render_seo_section(seo: dict) -> str:
    if not seo:
        return '<span class="not-found">No SEO data found.</span>'

    parts = []

    title = seo.get("title", "")
    if title:
        parts.append(f'<div class="info-row"><span class="info-label">Page Title</span><span class="info-value">{e(title)}</span></div>')

    canonical = seo.get("canonical", "")
    if canonical:
        parts.append(f'<div class="info-row"><span class="info-label">Canonical</span><span class="info-value" style="font-family:ui-monospace,monospace;font-size:0.75rem">{e(canonical)}</span></div>')

    og_complete = seo.get("og_complete", False)
    parts.append(f'<div class="info-row"><span class="info-label">OG Tags Complete</span><span class="info-value">{render_badge(og_complete)}</span></div>')

    links = seo.get("links", {})
    if links:
        internal = links.get("internal", 0)
        external = links.get("external", 0)
        parts.append(f'<div class="info-row"><span class="info-label">Links</span><span class="info-value" style="font-family:ui-monospace,monospace;font-size:0.78rem">{internal} internal · {external} external</span></div>')

    schema_types = seo.get("schema_types", [])
    if schema_types:
        tags = "".join(f'<span class="tag">{e(s)}</span>' for s in schema_types)
        parts.append(f'<div class="info-row"><span class="info-label">Schema Types</span><div class="tags" style="margin-top:0.3rem">{tags}</div></div>')

    keywords = seo.get("top_keywords", [])
    if keywords:
        kw_html = "".join(
            f'<span class="keyword"><span class="kw-term">{e(k["term"])}</span><span class="kw-count">×{k["count"]}</span></span>'
            for k in keywords[:15]
        )
        parts.append(f'<div class="info-row"><span class="info-label">Top Keywords</span><div class="keyword-cloud">{kw_html}</div></div>')

    headings = seo.get("headings", {})
    heading_lines = []
    for tag in ("h1", "h2", "h3"):
        for text in headings.get(tag, []):
            heading_lines.append(f'<span class="hline {tag}">{e(text)}</span>')

    if heading_lines:
        outline_html = "\n".join(heading_lines[:20])
        parts.append(f'<div class="info-row"><span class="info-label">Heading Outline</span><div class="heading-outline" style="margin-top:0.4rem">{outline_html}</div></div>')

    return "\n".join(parts)


def render_competitor_section(data: dict) -> str:
    domain = data.get("domain", "")
    scraped = data.get("scraped", {})
    techstack = data.get("techstack", {})
    github = data.get("github", {})
    seo = data.get("seo", {})
    homepage = scraped.get("homepage", {})
    url = scraped.get("url", "")

    # Overview info card
    overview_rows = []
    hero = homepage.get("hero_text", "")
    if hero:
        overview_rows.append(f'<div class="info-row"><span class="info-label">Hero</span><span class="info-value">{e(hero)}</span></div>')
    cta = homepage.get("cta_text", "")
    if cta:
        overview_rows.append(f'<div class="info-row"><span class="info-label">CTA</span><span class="info-value">{e(cta)}</span></div>')
    meta_desc = homepage.get("meta_description", "")
    if meta_desc:
        overview_rows.append(f'<div class="info-row"><span class="info-label">Meta Description</span><span class="info-value">{e(meta_desc)}</span></div>')
    og_title = homepage.get("og_title", "")
    if og_title:
        overview_rows.append(f'<div class="info-row"><span class="info-label">OG Title</span><span class="info-value">{e(og_title)}</span></div>')
    if not overview_rows:
        overview_rows.append('<span class="not-found">No homepage data extracted.</span>')

    overview_card = f'<div class="info-card">{"".join(overview_rows)}</div>'

    # Features count info card (supplementary)
    features = scraped.get("features", {})
    feature_items = features.get("items", [])
    pricing = scraped.get("pricing", {})
    tiers = pricing.get("tiers", [])
    blog_found = scraped.get("blog", {}).get("found", False)

    meta_rows = []
    meta_rows.append(f'<div class="info-row"><span class="info-label">Pricing Tiers</span><span class="info-value" style="font-family:ui-monospace,monospace">{len(tiers)}</span></div>')
    meta_rows.append(f'<div class="info-row"><span class="info-label">Features Listed</span><span class="info-value" style="font-family:ui-monospace,monospace">{len(feature_items)}</span></div>')
    meta_rows.append(f'<div class="info-row"><span class="info-label">Blog Active</span><span class="info-value">{render_badge(blog_found)}</span></div>')
    scraped_at = scraped.get("scraped_at", "")
    if scraped_at:
        meta_rows.append(f'<div class="info-row"><span class="info-label">Scraped</span><span class="info-value" style="font-family:ui-monospace,monospace;font-size:0.73rem">{e(scraped_at[:10])}</span></div>')

    meta_card = f'<div class="info-card">{"".join(meta_rows)}</div>'

    return f"""<hr class="section-divider">
<section id="{e(domain)}" class="competitor-section">
  <h2 class="competitor-name">{e(domain)}</h2>
  <span class="competitor-url-line">{e(url)}</span>

  <span class="subsection-label">Overview</span>
  <div class="top-grid">
    {overview_card}
    {meta_card}
  </div>

  <span class="subsection-label">Pricing</span>
  {render_pricing_section(scraped)}

  <span class="subsection-label">Tech Stack</span>
  {render_tech_stack_section(techstack)}

  <span class="subsection-label">GitHub</span>
  {render_github_section(github)}

  <span class="subsection-label">SEO</span>
  <div class="info-card">{render_seo_section(seo)}</div>

  <span class="subsection-label">Blog</span>
  {render_blog_section(scraped)}
</section>"""


# ---------------------------------------------------------------------------
# Master comparison table
# ---------------------------------------------------------------------------
MASTER_HEADERS = [
    "Domain", "Hero", "Pricing", "Tiers", "Features",
    "Blog", "Frontend", "Analytics", "GitHub Org", "Top Stars",
    "Top Keywords", "OG",
]


def render_master_table(competitors: list[dict]) -> str:
    header_cells = "".join(f"<th>{e(h)}</th>" for h in MASTER_HEADERS)

    rows = []
    for data in competitors:
        domain = data.get("domain", "")
        scraped = data.get("scraped", {})
        techstack = data.get("techstack", {}).get("stack", {})
        github = data.get("github", {})
        seo = data.get("seo", {})

        tiers = scraped.get("pricing", {}).get("tiers", [])
        pricing_summary = "; ".join(f"{t['name']} {t['price']}" for t in tiers[:3]) if tiers else "—"

        top_stars = ""
        if github.get("top_repos"):
            top_stars = str(github["top_repos"][0].get("stars", ""))

        top_kw = ", ".join(k["term"] for k in seo.get("top_keywords", [])[:5])
        blog_active = scraped.get("blog", {}).get("found", False)
        og_complete = seo.get("og_complete", False)
        hero = scraped.get("homepage", {}).get("hero_text", "")[:80]

        cells = [
            f'<td class="domain-cell"><a href="#{e(domain)}">{e(domain)}</a></td>',
            f'<td class="wrap">{e(hero)}</td>',
            f'<td class="wrap">{e(pricing_summary)}</td>',
            f'<td class="mono">{len(tiers)}</td>',
            f'<td class="mono">{len(scraped.get("features", {}).get("items", []))}</td>',
            f'<td>{render_badge(blog_active)}</td>',
            f'<td class="wrap">{e(", ".join(techstack.get("frontend", [])))}</td>',
            f'<td class="wrap">{e(", ".join(techstack.get("analytics", [])))}</td>',
            f'<td class="mono">{e(github.get("org", ""))}</td>',
            f'<td class="mono">{e(top_stars)}</td>',
            f'<td class="wrap">{e(top_kw)}</td>',
            f'<td>{render_badge(og_complete)}</td>',
        ]
        rows.append(f'<tr>{"".join(cells)}</tr>')

    rows_html = "\n".join(rows)
    return f"""<div class="table-scroll">
  <table class="data-table">
    <thead><tr>{header_cells}</tr></thead>
    <tbody>{rows_html}</tbody>
  </table>
</div>"""


# ---------------------------------------------------------------------------
# Full HTML assembly
# ---------------------------------------------------------------------------
def render_html(competitors: list[dict]) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    n = len(competitors)

    sidebar_links = (
        '<a class="nav-link overview-link" href="#master">Overview</a>'
        '<span class="nav-section-label">Competitors</span>'
    )
    for data in competitors:
        domain = data.get("domain", "")
        sidebar_links += f'<a class="nav-link" href="#{e(domain)}">{e(domain)}</a>'

    master_section = f"""<section id="master">
  <h2 class="section-heading">Master Comparison</h2>
  {render_master_table(competitors)}
</section>"""

    competitor_sections = "\n\n".join(render_competitor_section(c) for c in competitors)

    main_content = f"""<header class="report-header">
  <h1>Scout <span>Report</span></h1>
  <span class="report-meta">{e(now)} &nbsp;·&nbsp; {n} competitor{"s" if n != 1 else ""}</span>
</header>

{master_section}

{competitor_sections}"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Scout</title>
  <style>{CSS_BLOCK}</style>
</head>
<body>
  <nav class="sidebar">
    <div class="sidebar-logo">Scout</div>
    <div class="sidebar-meta">{e(now)} · {n} competitor{"s" if n != 1 else ""}</div>
    {sidebar_links}
  </nav>
  <main class="content">
    {main_content}
  </main>
  <script>{JS_BLOCK}</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def export(output_path: Path = DEFAULT_OUTPUT) -> Path:
    competitors = load_competitor_data()
    if not competitors:
        print("No competitor data found in .tmp/scraped/ — run scrape_competitor.py first.")
        return output_path
    output_path.parent.mkdir(exist_ok=True)
    html_content = render_html(competitors)
    output_path.write_text(html_content, encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Export competitor research to a self-contained HTML report.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output HTML file path")
    args = parser.parse_args()

    output_path = Path(args.output)
    result = export(output_path=output_path)
    print(f"Report written to: {result}")


if __name__ == "__main__":
    main()
