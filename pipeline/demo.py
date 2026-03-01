"""Demo mode: run full collect→analyze pipeline in-memory, print digest to stdout.

No files are persisted — no raw JSONL, no digest file, no seen_urls mutation.
"""
from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from pathlib import Path

from pipeline.analyze import (
    _hours_old,
    apply_hard_cap,
    generate_digest,
    keyword_density,
    keyword_match,
    signal_score,
)
from pipeline.collect import collect_all, normalize_url
from pipeline.dedup import SeenUrls, dedup_items


def run_demo(config: dict | None = None) -> str:
    """Run the full pipeline in demo mode and return the digest string.

    If config is None, tries resolve_config(); on any exception falls back to
    an empty config (HN Algolia only, no keyword filter).
    Results are not saved to disk.
    """
    # Step 1: resolve config
    if config is None:
        try:
            from pipeline.config import resolve_config
            config = resolve_config()
        except Exception:
            config = {"feeds": [], "keywords": {}, "scoring": {}}

    keywords: dict[str, list[str]] = config.get("keywords", {})
    source_weights: dict[str, float] = {
        feed["name"]: feed.get("weight", 0.1)
        for feed in config.get("feeds", [])
    }

    # Step 2: collect with fast-fail params
    print("[demo] Collecting items (timeout=3, retries=1)...")
    items = collect_all(config, timeout=3, retries=1)

    # Step 3: normalize URLs, drop empty
    for item in items:
        item.url = normalize_url(item.url)
    items = [item for item in items if item.url]

    total_collected = len(items)

    # Step 4: throwaway SeenUrls (never saved — writes only to temp dir)
    tmp_dir = Path(tempfile.mkdtemp())
    dummy_seen = SeenUrls(tmp_dir / "seen_urls.txt")

    # Step 5: dedup within batch (title similarity + URL hash)
    deduped = dedup_items(items, dummy_seen)

    # Step 6: keyword filter (only if keywords configured)
    if keywords:
        filtered: list[dict] = []
        for item_obj in deduped:
            topics = keyword_match(item_obj.title, keywords)
            if not topics:
                continue
            d = item_obj.to_dict()
            d["topics"] = sorted(topics)
            filtered.append(d)
    else:
        # No keywords — keep all items, label as uncategorized
        filtered = []
        for item_obj in deduped:
            d = item_obj.to_dict()
            d["topics"] = []
            filtered.append(d)

    total_filtered = len(filtered)

    # Step 7: signal scoring
    scored: list[dict] = []
    for item in filtered:
        item["hours_old"] = _hours_old(item)
        item["is_release"] = item.get("extra", {}).get("is_release", False)
        item["keyword_density"] = keyword_density(item.get("title", ""), keywords)
        item["score"] = signal_score(item, source_weights)
        scored.append(item)

    # Step 8: hard cap at 10
    final = apply_hard_cap(scored, max_items=10)
    kept = len(final)

    # Step 9: build stats and generate digest
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    stats = {
        "collected": total_collected,
        "filtered": total_filtered,
        "kept": kept,
        "cost": 0.0,
    }
    digest = generate_digest(final, date, stats)

    # Replace title line with demo banner
    digest = digest.replace(
        f"# News Digest — {date}",
        f"# Herald Demo — {date} (live fetch, not saved)",
        1,
    )

    # Step 10: append footer
    digest += "\n_Demo run — results not saved. Run `/news init` for daily scheduled digests._\n"

    # Step 11: prepend no-keywords note after stats line (if keywords were empty)
    if not keywords:
        lines = digest.splitlines(keepends=True)
        insert_idx = None
        for i, line in enumerate(lines):
            if line.startswith("_Collected:"):
                insert_idx = i + 1
                break
        if insert_idx is not None:
            note = "\n> No topics configured — showing trending items. Run `/news init <topic>` for domain-specific results.\n"
            lines.insert(insert_idx, note)
            digest = "".join(lines)

    return digest


def main() -> None:
    """CLI entrypoint: print demo digest to stdout."""
    print(run_demo())


if __name__ == "__main__":
    main()
