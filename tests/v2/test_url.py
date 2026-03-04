from __future__ import annotations

from herald.url import canonicalize_url


def test_lowercase_host():
    assert canonicalize_url("https://Example.COM/path") == "https://example.com/path"


def test_strip_www():
    assert canonicalize_url("https://www.example.com/p") == "https://example.com/p"


def test_strip_utm():
    assert canonicalize_url("https://x.com/p?utm_source=tw&id=1") == "https://x.com/p?id=1"


def test_strip_fbclid():
    assert canonicalize_url("https://x.com/p?fbclid=abc&q=1") == "https://x.com/p?q=1"


def test_sort_query_params():
    assert canonicalize_url("https://x.com/?z=1&a=2") == "https://x.com/?a=2&z=1"


def test_strip_fragment():
    assert canonicalize_url("https://x.com/p#section") == "https://x.com/p"


def test_keep_hashbang():
    assert canonicalize_url("https://x.com/#!/page") == "https://x.com/#!/page"


def test_http_to_https():
    assert canonicalize_url("http://example.com/p") == "https://example.com/p"


def test_strip_trailing_slash():
    assert canonicalize_url("https://x.com/path/") == "https://x.com/path"


def test_keep_root_slash():
    assert canonicalize_url("https://x.com/") == "https://x.com/"


def test_strip_default_port():
    assert canonicalize_url("https://x.com:443/p") == "https://x.com/p"


def test_strip_port_80():
    assert canonicalize_url("http://x.com:80/p") == "https://x.com/p"


def test_percent_decode_unreserved():
    assert canonicalize_url("https://x.com/%7Euser") == "https://x.com/~user"


def test_strip_ref_and_source():
    assert canonicalize_url("https://x.com/p?ref=tw&source=hn&id=1") == "https://x.com/p?id=1"


def test_combined():
    url = "http://WWW.Example.COM:80/path/?utm_source=x&b=2&a=1&ref=y#frag"
    assert canonicalize_url(url) == "https://example.com/path?a=1&b=2"
