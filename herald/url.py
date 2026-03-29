"""URL canonicalization — 10 rules from design doc."""
from __future__ import annotations

import re
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

_STRIP_PARAMS = frozenset({
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "utm_cid", "utm_reader", "utm_name", "utm_social", "utm_social-type",
    "fbclid", "gclid", "gclsrc", "ref", "source",
})

_UNRESERVED = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"
)


def _decode_unreserved(s: str) -> str:
    """Percent-decode unreserved characters (RFC 3986 §2.3)."""
    def _repl(m):
        ch = chr(int(m.group(1), 16))
        return ch if ch in _UNRESERVED else m.group(0)
    return re.sub(r"%([0-9A-Fa-f]{2})", _repl, s)


def canonicalize_url(url: str) -> str:
    p = urlparse(url)

    # Rule 6: http → https
    scheme = "https"

    # Rule 1: lowercase host
    host = p.hostname or ""
    # Rule 2: strip www. (exact prefix)
    if host.startswith("www."):
        host = host[4:]

    # Rule 8: strip default ports
    port = p.port
    if port in (80, 443, None):
        netloc = host
    else:
        netloc = f"{host}:{port}"

    # Rule 9: percent-decode unreserved chars in path
    path = _decode_unreserved(p.path)

    # Normalize empty path to "/"
    if not path:
        path = "/"

    # Rule 7: strip trailing slash (except root)
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    # Rule 5: strip fragment (except #! hashbang)
    fragment = p.fragment if p.fragment.startswith("!") else ""

    # Rule 3+13: remove tracking params
    if p.query:
        params = parse_qs(p.query, keep_blank_values=True)
        filtered = {
            k: v for k, v in params.items()
            if k.lower() not in _STRIP_PARAMS
        }
        # Rule 4: sort remaining params
        query = urlencode(sorted(filtered.items()), doseq=True)
    else:
        query = ""

    return urlunparse((scheme, netloc, path, "", query, fragment))
