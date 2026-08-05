from unittest.mock import MagicMock

from tools.detect_tech_stack import (
    categorize_technologies,
    extract_domain,
    infer_email_provider,
    probe_path_hints,
)


def test_extract_domain():
    assert extract_domain("https://www.linear.app/pricing") == "linear.app"


def test_categorize_puts_react_in_frontend():
    raw = {"React": {"categories": ["JavaScript frameworks"]}}
    assert "React" in categorize_technologies(raw)["frontend"]


def test_categorize_puts_ga_in_analytics():
    raw = {"Google Analytics": {"categories": ["Analytics"]}}
    assert "Google Analytics" in categorize_technologies(raw)["analytics"]


def test_categorize_puts_cloudflare_in_cdn():
    raw = {"Cloudflare": {"categories": ["CDN"]}}
    assert "Cloudflare" in categorize_technologies(raw)["cdn"]


def test_categorize_puts_stripe_in_payments():
    raw = {"Stripe": {"categories": ["Payment processors"]}}
    assert "Stripe" in categorize_technologies(raw)["payments"]


def test_categorize_puts_wordpress_in_cms():
    raw = {"WordPress": {"categories": ["CMS", "Blog"]}}
    assert "WordPress" in categorize_technologies(raw)["cms"]


def test_categorize_unknown_goes_to_other():
    raw = {"SomeNewTool": {"categories": ["Something unknown"]}}
    assert "SomeNewTool" in categorize_technologies(raw)["other"]


def test_infer_email_provider_google():
    assert infer_email_provider(["aspmx.l.google.com"]) == "Google Workspace"


def test_infer_email_provider_microsoft():
    assert infer_email_provider(["company.mail.protection.outlook.com"]) == "Microsoft 365"


def test_infer_email_provider_unknown():
    assert infer_email_provider(["mail.somehost.com"]) == "Unknown"


def test_probe_path_hints_detects_nextjs():
    def mock_head(url):
        r = MagicMock()
        r.status_code = 200 if "_next" in url else 404
        return r

    assert "Next.js" in probe_path_hints("https://linear.app", mock_head)


def test_probe_path_hints_detects_wordpress():
    def mock_head(url):
        r = MagicMock()
        r.status_code = 200 if "wp-admin" in url else 404
        return r

    assert "WordPress" in probe_path_hints("https://example.com", mock_head)
