from unittest.mock import MagicMock

from tools.fetch_github_presence import (
    extract_domain,
    find_github_link_in_html,
    format_repo,
    get_primary_languages,
)


def test_extract_domain():
    assert extract_domain("https://linear.app") == "linear.app"


def test_find_github_link_in_html_finds_org():
    html = '<a href="https://github.com/linearapp">GitHub</a>'
    assert find_github_link_in_html(html) == "linearapp"


def test_find_github_link_in_html_returns_none_when_absent():
    html = "<a href='https://twitter.com/linear'>Twitter</a>"
    assert find_github_link_in_html(html) is None


def test_find_github_link_skips_generic_github_root():
    html = '<a href="https://github.com">GitHub</a>'
    assert find_github_link_in_html(html) is None


def test_format_repo():
    mock_repo = MagicMock()
    mock_repo.name = "linear-api"
    mock_repo.description = "The Linear API client"
    mock_repo.stargazers_count = 512
    mock_repo.language = "TypeScript"
    mock_repo.pushed_at.isoformat.return_value = "2026-07-01T00:00:00"
    result = format_repo(mock_repo)
    assert result == {
        "name": "linear-api",
        "description": "The Linear API client",
        "stars": 512,
        "language": "TypeScript",
        "last_push": "2026-07-01T00:00:00",
    }


def test_get_primary_languages_sorts_by_count():
    mock_repos = [MagicMock(language=lang) for lang in ["TypeScript", "TypeScript", "Python", "Go", "TypeScript"]]
    result = get_primary_languages(mock_repos)
    assert result[0] == "TypeScript"
    assert "Python" in result
    assert "Go" in result


def test_get_primary_languages_excludes_none():
    mock_repos = [MagicMock(language=None), MagicMock(language="Rust")]
    result = get_primary_languages(mock_repos)
    assert result == ["Rust"]
