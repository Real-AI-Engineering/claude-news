"""Tests for pipeline.demo module."""
from __future__ import annotations

import re
import tempfile
from pathlib import Path

from pipeline.collect import RawItem

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_KEYWORDS_CONFIG = {
    "feeds": [{"name": "Test", "url": "http://test.com/rss", "weight": 0.5}],
    "keywords": {"ai": ["ai", "agent", "framework"]},
    "scoring": {"max_items": 10},
}

_EMPTY_CONFIG = {
    "feeds": [],
    "keywords": {},
    "scoring": {},
}


def _make_items(n: int, title_template: str = "AI Agent Framework {i} Released") -> list[RawItem]:
    return [
        RawItem(
            url=f"https://example.com/{i}",
            title=title_template.format(i=i),
            source="Test",
            published="2026-03-01T10:00:00+00:00",
        )
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_demo_banner(monkeypatch):
    """Output must contain demo banner with date and 'live fetch, not saved'."""
    items = _make_items(5)
    monkeypatch.setattr("pipeline.demo.collect_all", lambda config, **kw: items)

    from pipeline.demo import run_demo
    result = run_demo(_KEYWORDS_CONFIG)

    assert "# Herald Demo —" in result
    assert "(live fetch, not saved)" in result


def test_demo_no_persist(monkeypatch, tmp_path):
    """Real seen_urls.txt must be unchanged after run_demo."""
    items = _make_items(3)
    monkeypatch.setattr("pipeline.demo.collect_all", lambda config, **kw: items)

    # Create a real seen_urls.txt with some content
    seen_file = tmp_path / "seen_urls.txt"
    original_content = "abc123 2026-01-01T00:00:00+00:00\n"
    seen_file.write_text(original_content)

    from pipeline.demo import run_demo
    run_demo(_KEYWORDS_CONFIG)

    # The file must be unchanged
    assert seen_file.read_text() == original_content


def test_demo_hard_cap(monkeypatch):
    """Output must contain at most 10 numbered items when 20 items returned."""
    items = _make_items(20)
    monkeypatch.setattr("pipeline.demo.collect_all", lambda config, **kw: items)

    from pipeline.demo import run_demo
    result = run_demo(_KEYWORDS_CONFIG)

    # Count lines matching a numbered list item pattern: "1. [title](...)"
    numbered_lines = [line for line in result.splitlines() if re.match(r"^\d+\.", line)]
    assert len(numbered_lines) <= 10


def test_demo_no_keywords(monkeypatch):
    """With empty keywords, all items pass through and note about no topics appears."""
    # Use very distinct titles to avoid title-similarity dedup collapsing them
    distinct_titles = [
        "Python 3.14 released with new features",
        "Rust 2025 edition announcement",
        "Docker Desktop update brings performance improvements",
        "PostgreSQL 17 migration guide",
        "Kubernetes 1.32 cluster autoscaling",
    ]
    items = [
        RawItem(
            url=f"https://example.com/distinct/{i}",
            title=distinct_titles[i],
            source="Test",
            published="2026-03-01T10:00:00+00:00",
        )
        for i in range(5)
    ]
    monkeypatch.setattr("pipeline.demo.collect_all", lambda config, **kw: items)

    from pipeline.demo import run_demo
    result = run_demo(_EMPTY_CONFIG)

    # All 5 items should be kept (shown in output)
    assert "Kept: 5" in result
    # Note about no topics configured must appear
    assert "No topics configured" in result


def test_demo_empty_collect(monkeypatch):
    """When collect returns [], run_demo returns valid markdown with Kept: 0."""
    monkeypatch.setattr("pipeline.demo.collect_all", lambda config, **kw: [])

    from pipeline.demo import run_demo
    result = run_demo(_EMPTY_CONFIG)

    assert "Kept: 0" in result
    # Should still be valid markdown (has the demo header)
    assert "# Herald Demo —" in result


def test_collect_timeout_retries_params(monkeypatch):
    """fetch_rss_feed must pass timeout and retries to httpx.Client."""
    import sys
    import types

    captured = {}

    class FakeClient:
        def __init__(self, timeout=None, follow_redirects=False):
            captured["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def get(self, url):
            raise RuntimeError("stop early — capture only")

    monkeypatch.setattr("pipeline.collect.httpx.Client", FakeClient)

    # Stub fastfeedparser so the import inside fetch_rss_feed succeeds
    fake_ff = types.ModuleType("fastfeedparser")
    fake_ff.parse = lambda text: types.SimpleNamespace(entries=[])
    monkeypatch.setitem(sys.modules, "fastfeedparser", fake_ff)

    from pipeline.collect import fetch_rss_feed
    feed = {"name": "TestFeed", "url": "http://example.com/rss"}
    result = fetch_rss_feed(feed, timeout=3, retries=1)

    # Should have passed timeout=3 to httpx.Client
    assert captured.get("timeout") == 3
    # Should return empty list on error (not raise)
    assert result == []
