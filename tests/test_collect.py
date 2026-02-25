"""Tests for collect module."""
import json
from pathlib import Path

def test_normalize_url_strips_utm():
    from pipeline.collect import normalize_url
    assert normalize_url("https://example.com/page?utm_source=x&utm_medium=y") == "https://example.com/page"

def test_normalize_url_strips_ref():
    from pipeline.collect import normalize_url
    assert normalize_url("https://example.com/page?ref=abc") == "https://example.com/page"

def test_normalize_url_strips_trailing_slash():
    from pipeline.collect import normalize_url
    assert normalize_url("https://example.com/page/") == "https://example.com/page"

def test_normalize_url_forces_https():
    from pipeline.collect import normalize_url
    assert normalize_url("http://example.com/page") == "https://example.com/page"

def test_normalize_url_preserves_query_params():
    from pipeline.collect import normalize_url
    assert normalize_url("https://example.com/page?id=123&utm_source=x") == "https://example.com/page?id=123"

def test_normalize_url_rejects_javascript_scheme():
    from pipeline.collect import normalize_url
    assert normalize_url("javascript:alert(1)") == ""

def test_normalize_url_rejects_data_scheme():
    from pipeline.collect import normalize_url
    assert normalize_url("data:text/html,<h1>hi</h1>") == ""

def test_normalize_url_rejects_file_scheme():
    from pipeline.collect import normalize_url
    assert normalize_url("file:///etc/passwd") == ""

def test_item_schema():
    from pipeline.collect import RawItem
    item = RawItem(
        url="https://example.com",
        title="Test",
        source="test",
        published="2026-02-25T00:00:00Z",
    )
    d = item.to_dict()
    assert all(k in d for k in ["url", "title", "source", "published", "collected_at"])
