from tools.scrape_competitor import (
    extract_domain,
    extract_blog_data,
    extract_features_data,
    extract_homepage_data,
    extract_pricing_data,
    find_nav_link,
)

HOMEPAGE_HTML = """
<html>
<head>
  <meta name="description" content="The best writing tool">
  <meta property="og:title" content="Writesonic">
  <meta property="og:description" content="AI writing assistant">
</head>
<body>
  <h1>Write better content faster</h1>
  <a href="/pricing">Get started free</a>
</body>
</html>
"""

PRICING_HTML = """
<html><body>
  <div class="plan">
    <h3>Starter</h3>
    <p>$19/mo</p>
    <ul><li>10,000 words</li><li>5 users</li></ul>
  </div>
  <div class="plan">
    <h3>Pro</h3>
    <p>$49/mo</p>
    <ul><li>Unlimited words</li></ul>
  </div>
</body></html>
"""

FEATURES_HTML = """
<html><body>
  <h2>AI Writing</h2><p>Generate content in seconds</p>
  <h2>SEO Optimizer</h2><p>Rank higher in search</p>
</body></html>
"""

BLOG_HTML = """
<html><body>
  <article class="post">
    <h3>Top 10 AI Writing Tips</h3>
    <time class="date">2026-07-01</time>
    <p>Here are the best tips for writing with AI...</p>
  </article>
  <article class="post">
    <h3>How to Write Faster</h3>
    <time class="date">2026-06-15</time>
    <p>Speed up your writing process with these strategies...</p>
  </article>
</body></html>
"""


def test_extract_domain():
    assert extract_domain("https://www.writesonic.com/pricing") == "writesonic.com"


def test_extract_homepage_meta_description():
    data = extract_homepage_data(HOMEPAGE_HTML, "https://writesonic.com")
    assert data["meta_description"] == "The best writing tool"


def test_extract_homepage_og_title():
    data = extract_homepage_data(HOMEPAGE_HTML, "https://writesonic.com")
    assert data["og_title"] == "Writesonic"


def test_extract_homepage_hero_text():
    data = extract_homepage_data(HOMEPAGE_HTML, "https://writesonic.com")
    assert data["hero_text"] == "Write better content faster"


def test_extract_homepage_cta():
    data = extract_homepage_data(HOMEPAGE_HTML, "https://writesonic.com")
    assert "free" in data["cta_text"].lower()


def test_extract_pricing_finds_tiers():
    data = extract_pricing_data(PRICING_HTML, "https://writesonic.com/pricing")
    assert data["found"] is True
    assert len(data["tiers"]) == 2


def test_extract_pricing_tier_names():
    data = extract_pricing_data(PRICING_HTML, "https://writesonic.com/pricing")
    names = [t["name"] for t in data["tiers"]]
    assert "Starter" in names
    assert "Pro" in names


def test_extract_pricing_tier_prices():
    data = extract_pricing_data(PRICING_HTML, "https://writesonic.com/pricing")
    starter = next(t for t in data["tiers"] if t["name"] == "Starter")
    assert "$19/mo" in starter["price"]


def test_extract_features_items():
    data = extract_features_data(FEATURES_HTML, "https://writesonic.com/features")
    assert data["found"] is True
    headings = [i["heading"] for i in data["items"]]
    assert "AI Writing" in headings
    assert "SEO Optimizer" in headings


def test_extract_blog_posts():
    data = extract_blog_data(BLOG_HTML, "https://writesonic.com/blog")
    assert data["found"] is True
    assert len(data["posts"]) == 2
    assert data["posts"][0]["title"] == "Top 10 AI Writing Tips"


def test_find_nav_link_matches_keyword():
    links = ["https://writesonic.com/about", "https://writesonic.com/pricing", "https://writesonic.com/blog"]
    result = find_nav_link(links, ["pricing", "price", "plans"], "https://writesonic.com")
    assert result == "https://writesonic.com/pricing"


def test_find_nav_link_returns_none_when_missing():
    links = ["https://writesonic.com/about", "https://writesonic.com/contact"]
    result = find_nav_link(links, ["pricing", "plans"], "https://writesonic.com")
    assert result is None
