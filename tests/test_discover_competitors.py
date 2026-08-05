import json
from unittest.mock import MagicMock, patch

from tools.discover_competitors import (
    build_queries,
    deduplicate,
    extract_domain,
    is_noise_domain,
    parse_seed_url,
    search_ddg,
)


def test_extract_domain_full_url():
    assert extract_domain("https://www.notion.so/pricing") == "notion.so"


def test_extract_domain_no_scheme():
    assert extract_domain("notion.so") == "notion.so"


def test_is_noise_domain_known_noise():
    assert is_noise_domain("wikipedia.org") is True


def test_is_noise_domain_subdomain_of_noise():
    assert is_noise_domain("en.wikipedia.org") is True


def test_is_noise_domain_real_company():
    assert is_noise_domain("notion.so") is False


def test_deduplicate_removes_duplicate_domain():
    competitors = [
        {"domain": "notion.so", "url": "https://notion.so", "name": "Notion", "discovered_via": "q1"},
        {"domain": "notion.so", "url": "https://notion.so/pricing", "name": "Notion 2", "discovered_via": "q2"},
    ]
    result = deduplicate(competitors)
    assert len(result) == 1
    assert result[0]["url"] == "https://notion.so"


def test_deduplicate_keeps_unique_domains():
    competitors = [
        {"domain": "notion.so", "url": "https://notion.so", "name": "Notion", "discovered_via": "q1"},
        {"domain": "coda.io", "url": "https://coda.io", "name": "Coda", "discovered_via": "q1"},
    ]
    assert len(deduplicate(competitors)) == 2


def test_build_queries():
    queries = build_queries("project management software")
    assert queries == [
        "project management software",
        "project management software alternatives",
        "best project management software tools",
    ]


def test_parse_seed_url_uses_meta_description():
    html = '<html><head><meta name="description" content="The best workspace"></head><body></body></html>'
    assert parse_seed_url(html, "https://notion.so") == "The best workspace"


def test_parse_seed_url_falls_back_to_h1():
    html = "<html><head></head><body><h1>All-in-one workspace</h1></body></html>"
    assert parse_seed_url(html, "https://notion.so") == "All-in-one workspace"


def test_parse_seed_url_falls_back_to_domain():
    html = "<html><head></head><body></body></html>"
    assert parse_seed_url(html, "https://notion.so") == "notion.so"


@patch("tools.discover_competitors.DDGS")
def test_search_ddg_filters_noise_domains(mock_ddgs_class):
    mock_ddgs = MagicMock()
    mock_ddgs_class.return_value.__enter__.return_value = mock_ddgs
    mock_ddgs.text.return_value = [
        {"href": "https://notion.so", "title": "Notion"},
        {"href": "https://reddit.com/r/productivity", "title": "Reddit thread"},
    ]
    results = search_ddg("note taking app")
    assert len(results) == 1
    assert results[0]["domain"] == "notion.so"


@patch("tools.discover_competitors.DDGS")
def test_search_ddg_sets_discovered_via(mock_ddgs_class):
    mock_ddgs = MagicMock()
    mock_ddgs_class.return_value.__enter__.return_value = mock_ddgs
    mock_ddgs.text.return_value = [{"href": "https://notion.so", "title": "Notion"}]
    results = search_ddg("note app")
    assert results[0]["discovered_via"] == "query: note app"
