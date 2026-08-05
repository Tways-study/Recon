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
