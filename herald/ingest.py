"""Herald v2 Ingest Stage: RawItem -> article UPSERT pipeline."""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from urllib.parse import urlparse as _urlparse

from herald.db import Database
from herald.models import RawItem, Source
from herald.scoring import article_score_base
from herald.topics import extract_topics
from herald.ulid import generate_ulid
from herald.url import canonicalize_url

_RELEASE_KEYWORDS = frozenset(
    {"release", "launches", "launch", "v1.", "v2.", "v3.", "version", "ships", "shipped"}
)

_TITLE_MAX_LEN = 500

# Patterns that indicate prompt injection attempts in titles.
# Each pattern is stripped (not the whole title dropped) from the title text.
_INJECTION_PATTERNS: list[re.Pattern] = [
    re.compile(r"ignore\s+previous", re.IGNORECASE),
    re.compile(r"system\s*:", re.IGNORECASE),
    re.compile(r"\b(user|assistant|human|ai)\s*:", re.IGNORECASE),
    re.compile(r"!\["),                                  # markdown image tag
]

# Base64 blob detection uses a linear scan rather than lookahead-based regex to
# avoid catastrophic backtracking (ReDoS) on adversarial inputs.
_B64_CHARS = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=")
_B64_MIN_LEN = 30


def _contains_base64_blob(s: str) -> bool:
    """Return True if *s* contains a run of 30+ base64-alphabet chars with mixed case+digits."""
    run_start = -1
    for i, ch in enumerate(s):
        if ch in _B64_CHARS:
            if run_start == -1:
                run_start = i
        else:
            if run_start != -1 and (i - run_start) >= _B64_MIN_LEN:
                segment = s[run_start:i].rstrip("=")
                if (
                    any(c.isupper() for c in segment)
                    and any(c.islower() for c in segment)
                    and any(c.isdigit() for c in segment)
                ):
                    return True
            run_start = -1
    # Check final run
    if run_start != -1 and (len(s) - run_start) >= _B64_MIN_LEN:
        segment = s[run_start:].rstrip("=")
        if (
            any(c.isupper() for c in segment)
            and any(c.islower() for c in segment)
            and any(c.isdigit() for c in segment)
        ):
            return True
    return False

_ALLOWED_URL_SCHEMES = frozenset({"http", "https"})


def _sanitize_title(title: str) -> str:
    """Strip null bytes and injection patterns from *title*.

    Returns the cleaned title string (may be empty if everything was stripped).
    Callers must drop the item when the returned value is empty or whitespace.
    """
    # Strip null bytes
    title = title.replace("\x00", "")

    # Strip injection patterns
    for pattern in _INJECTION_PATTERNS:
        title = pattern.sub("", title)

    # Strip base64 blobs (linear scan to avoid ReDoS)
    if _contains_base64_blob(title):
        # Remove individual runs of base64-alphabet chars >= 30 chars
        title = re.sub(r"[A-Za-z0-9+/]{30,}={0,2}", "", title)

    # Collapse runs of whitespace left after stripping
    title = re.sub(r"\s{2,}", " ", title).strip()

    return title

_TYPE_KEYWORDS: dict[str, frozenset[str]] = {
    "release": _RELEASE_KEYWORDS,
    "research": frozenset({"paper", "arxiv", "study", "survey", "benchmark"}),
    "opinion": frozenset({"opinion", "editorial", "why ", "how ", "thoughts on"}),
    "tutorial": frozenset({"tutorial", "guide", "how to", "howto", "step by step"}),
}


def _detect_release(title: str) -> bool:
    t = title.lower()
    return any(kw in t for kw in _RELEASE_KEYWORDS)


def _detect_type(title: str) -> str:
    t = title.lower()
    for story_type, keywords in _TYPE_KEYWORDS.items():
        if any(kw in t for kw in keywords):
            return story_type
    return "news"


@dataclass
class IngestResult:
    articles_new: int = 0
    articles_updated: int = 0


def ingest_items(
    db: Database,
    items: list[RawItem],
    sources: dict[str, Source],
    topic_rules: dict[str, list[str]] | None = None,
) -> IngestResult:
    result = IngestResult()
    now = int(time.time())

    with db.transaction():
        for item in items:
            source = sources.get(item.source_id)
            if source is None:
                continue

            # Reject URLs containing null bytes
            if "\x00" in item.url:
                continue

            # Validate URL — only hierarchical http/https with a non-empty hostname
            # and no whitespace, quotes, or control characters.
            try:
                _parsed = _urlparse(item.url)
                _scheme = _parsed.scheme.lower()
            except Exception:
                continue
            if _scheme not in _ALLOWED_URL_SCHEMES:
                continue
            if not _parsed.hostname:
                continue
            # Reject URLs containing whitespace, quotes, or control characters
            if any(c in item.url for c in (' ', '\t', '\n', '\r', '"', "'")):
                continue
            if any(ord(c) < 0x20 for c in item.url):
                continue

            try:
                url_canonical = canonicalize_url(item.url)
            except Exception:
                continue

            # Sanitize and truncate title
            title = _sanitize_title(item.title)
            if not title:
                continue
            if len(title) > _TITLE_MAX_LEN:
                title = title[:_TITLE_MAX_LEN]

            # Pre-check: does this canonical URL already exist?
            existing = db.execute(
                "SELECT id, points FROM articles WHERE url_canonical = ?",
                (url_canonical,),
            ).fetchone()

            is_release = _detect_release(title)
            story_type = _detect_type(title)
            extra_json = json.dumps(item.extra) if item.extra else None

            if existing is None:
                # New article
                article_id = generate_ulid()
                score = article_score_base(
                    source_weight=source.weight,
                    points=item.points,
                    keyword_density=0.0,
                    is_release=is_release,
                )
                db.execute(
                    """
                    INSERT INTO articles
                        (id, url_original, url_canonical, title, origin_source_id,
                         published_at, collected_at, points, story_type, score_base,
                         scored_at, extra)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        article_id,
                        item.url,
                        url_canonical,
                        title,
                        item.source_id,
                        item.published_at,
                        now,
                        item.points,
                        story_type,
                        score,
                        now,
                        extra_json,
                    ),
                )
                result.articles_new += 1
            else:
                # Existing article — update only if new points are higher
                article_id = existing[0]
                existing_points = existing[1]
                effective_points = max(existing_points, item.points)
                score = article_score_base(
                    source_weight=source.weight,
                    points=effective_points,
                    keyword_density=0.0,
                    is_release=is_release,
                )
                if item.points > existing_points:
                    db.execute(
                        """
                        UPDATE articles
                        SET points = ?,
                            score_base = ?,
                            scored_at = ?
                        WHERE id = ?
                        """,
                        (effective_points, score, now, article_id),
                    )
                result.articles_updated += 1

            # Insert mention (ignore duplicates — same article+source)
            db.execute(
                """
                INSERT OR IGNORE INTO mentions
                    (article_id, source_id, url, points, discovered_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (article_id, item.source_id, item.url, item.points, now),
            )

            # Assign topics
            if topic_rules:
                topics = extract_topics(title, topic_rules)
                for topic in topics:
                    db.execute(
                        "INSERT OR IGNORE INTO article_topics (article_id, topic) VALUES (?, ?)",
                        (article_id, topic),
                    )

    return result
