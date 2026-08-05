from bs4 import BeautifulSoup

from tools.analyze_seo import (
    check_og_complete,
    count_keywords,
    count_links,
    extract_headings,
    extract_schema_types,
    extract_title,
)

FULL_HTML = """
<html>
<head>
  <title>Writesonic — AI Writing Tool</title>
  <meta name="description" content="Write better content faster with AI">
  <link rel="canonical" href="https://writesonic.com">
  <meta property="og:title" content="Writesonic">
  <meta property="og:description" content="AI writing assistant">
  <meta property="og:image" content="https://writesonic.com/og.png">
  <script type="application/ld+json">{"@type": "Organization"}</script>
</head>
<body>
  <h1>AI Writing Tool</h1>
  <h2>Features</h2>
  <h2>Pricing</h2>
  <h3>Blog</h3>
  <p>Write content faster with our AI writing assistant tool for your business</p>
  <a href="/pricing">Pricing</a>
  <a href="/features">Features</a>
  <a href="https://example.com">External</a>
</body>
</html>
"""


def test_extract_title():
    soup = BeautifulSoup(FULL_HTML, "lxml")
    assert extract_title(soup) == "Writesonic — AI Writing Tool"


def test_extract_headings_h1():
    soup = BeautifulSoup(FULL_HTML, "lxml")
    headings = extract_headings(soup)
    assert headings["h1"] == ["AI Writing Tool"]


def test_extract_headings_h2_count():
    soup = BeautifulSoup(FULL_HTML, "lxml")
    assert len(extract_headings(soup)["h2"]) == 2


def test_extract_headings_h3():
    soup = BeautifulSoup(FULL_HTML, "lxml")
    assert extract_headings(soup)["h3"] == ["Blog"]


def test_count_keywords_top_terms():
    text = "write writing write content content faster AI AI AI tool"
    result = count_keywords(text, top_n=3)
    terms = [r["term"] for r in result]
    assert "ai" in terms
    assert len(result) == 3


def test_count_keywords_excludes_stopwords():
    text = "the best writing tool for the content team"
    result = count_keywords(text, top_n=10)
    terms = [r["term"] for r in result]
    assert "the" not in terms
    assert "for" not in terms


def test_count_links():
    soup = BeautifulSoup(FULL_HTML, "lxml")
    result = count_links(soup, "writesonic.com")
    assert result["internal"] == 2
    assert result["external"] == 1


def test_extract_schema_types():
    soup = BeautifulSoup(FULL_HTML, "lxml")
    assert "Organization" in extract_schema_types(soup)


def test_check_og_complete_true():
    soup = BeautifulSoup(FULL_HTML, "lxml")
    assert check_og_complete(soup) is True


def test_check_og_complete_false_when_missing_image():
    html = """<html><head>
      <meta property="og:title" content="X">
      <meta property="og:description" content="Y">
    </head></html>"""
    soup = BeautifulSoup(html, "lxml")
    assert check_og_complete(soup) is False
