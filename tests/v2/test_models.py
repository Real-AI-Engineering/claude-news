from __future__ import annotations

import time

from herald.ulid import generate_ulid
from herald.models import RawItem, Article, Source


def test_ulid_is_26_chars():
    assert len(generate_ulid()) == 26


def test_ulid_sortable_by_time():
    a = generate_ulid()
    time.sleep(0.002)
    b = generate_ulid()
    assert a < b


def test_ulid_unique():
    ids = {generate_ulid() for _ in range(100)}
    assert len(ids) == 100


def test_raw_item_fields():
    item = RawItem(url="https://x.com", title="Test", source_id="hn",
                   published_at=1000, points=50, extra=None)
    assert item.url == "https://x.com"
    assert item.source_id == "hn"


def test_source_defaults():
    s = Source(id="hn", name="Hacker News")
    assert s.weight == 0.2
    assert s.category == "community"
