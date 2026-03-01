# Herald — How It Works

## Overview

Herald is a six-command, one-skill, one-hook Claude Code plugin backed by a local Python pipeline. The pipeline runs on a system scheduler (launchd, systemd, or cron), fetches and scores news items, and writes a digest to local storage. Claude Code reads that digest on demand or on session start. No persistent server process is required.

## Components

### Commands (6)

| Command | Role |
|---------|------|
| `/news init [topic]` | Bootstrap: write config, install scheduler, run first fetch |
| `/news add <url\|topic>` | Add a feed URL or built-in topic pack to an existing config |
| `/news sources` | List configured sources with their tier and last-fetch status |
| `/news digest` | Read and display today's digest (fetches on-demand if not yet run) |
| `/news run` | Trigger an immediate fetch-and-analyze cycle |
| `/news stop` | Uninstall the scheduler; leave config and data intact |

### Skill: `news-digest`

A Claude Code skill that activates automatically when the session context contains phrases like "what's new", "latest trends", or "today's news". When triggered, it reads the most recent digest from `~/.local/share/herald/digests/` and formats it for the current conversation. No network call is made by the skill itself.

### Hook: `SessionStart`

Runs at the start of every Claude Code session. Checks whether a digest file exists for today's date. If one exists, prints a one-line reminder ("Herald digest ready — /news digest to read"). If none exists and the last fetch is more than 24 hours ago, prints a warning so the user knows to run `/news run`.

### Python Pipeline

All pipeline code is in the Herald package. The scheduler invokes `run.sh`, which orchestrates the two main stages.

**run.sh**
Shell orchestrator. Acquires a POSIX lockfile to prevent concurrent runs, calls `collect.py`, then `analyze.py`, filters verbose logs to warnings and above for the scheduler output, and prunes digest retention (keeps last 30 days by default).

**collect.py**
Fetches content from three source types:
- RSS/Atom feeds via `fastfeedparser` (async batch, retry with exponential backoff)
- HN Algolia API (`https://hn.algolia.com/api/v1/search`) for top stories matching configured keywords
- Tavily Search API (only if `TAVILY_API_KEY` is set) for supplemental web results

Each response is guarded at 10 MB. URLs are normalized (scheme-stripped, trailing-slash-normalized, query-param-filtered) before writing. Output is appended atomically to a date-partitioned JSONL file at `~/.local/share/herald/raw/YYYY-MM-DD.jsonl`.

**dedup.py**
Applied by `collect.py` before writing. Three layers:
1. URL hash — exact SHA-256 of the normalized URL; O(1) lookup in a bloom-filter-backed seen set
2. URL normalization — catches `http` vs `https`, `www.` prefix, trailing slashes
3. Title similarity — Jaccard similarity on trigrams; threshold 0.85; catches the same story from multiple feeds

**analyze.py**
Reads the raw JSONL for today, scores each item, and writes the digest.

Scoring formula per item:
```
score = source_weight
      + (hn_points / 100)        # normalized, cap 10
      + keyword_density           # matched keywords / total words, cap 0.3
      + release_flag              # 1.0 if title contains "release", "v\d", "launch", etc.
      + recency_decay             # 1.0 at publish time, 0.5 at 12h, 0.1 at 24h
```

Hard cap: top 10 items per digest. Items are grouped by the topic/feed they were fetched for. Output is written as a structured YAML digest to `~/.local/share/herald/digests/YYYY-MM-DD.yaml`.

**config.py**
Implements a two-layer overlay system:
- **Immutable preset layer** — bundled YAML files in the Herald package (e.g., `ai-engineering.yaml`, `rust.yaml`). Never modified by the user.
- **User override layer** — `~/.config/herald/config.yaml`. Only user additions and overrides live here.

At runtime, the two layers are merged: preset values provide defaults, user values win on conflict. This means Herald upgrades can update preset feeds without touching user customizations.

**scheduler.py**
Detects the platform and installs the appropriate scheduler:
- macOS: writes a launchd plist to `~/Library/LaunchAgents/dev.skill7.herald.plist` and loads it with `launchctl`
- Linux (systemd available): writes a systemd user unit and timer to `~/.config/systemd/user/`
- Linux (fallback): installs a crontab entry

Default schedule: daily at 07:00 local time. Configurable in `~/.config/herald/config.yaml`.

## Data Flow

```
[Scheduler] 07:00
     │
     ▼
  run.sh  (lockfile acquired)
     │
     ├─ collect.py
     │    ├─ RSS feeds → fastfeedparser → normalize → dedup → JSONL
     │    ├─ HN Algolia API → normalize → dedup → JSONL
     │    └─ Tavily API (if key set) → normalize → dedup → JSONL
     │
     └─ analyze.py
          └─ score → top-10 → group by topic → digest YAML
                                                    │
                             ┌──────────────────────┘
                             │
            [SessionStart hook] checks digest exists → reminder
            [/news digest]       reads digest → formatted output
            [news-digest skill]  reads digest → inline in conversation
```

## Trust Boundaries

- Herald fetches from the public internet. It does not authenticate to any feed server.
- Tavily queries are sent to `api.tavily.com` only when `TAVILY_API_KEY` is present and non-empty.
- The HN Algolia API is public and unauthenticated.
- All other data remains local. Herald does not phone home, report telemetry, or cache data outside `~/.config/herald/` and `~/.local/share/herald/`.
- The lockfile (`/tmp/herald.lock`) prevents concurrent pipeline runs.

## Limitations

- Digest is batch-based (once daily by default). Not suitable for real-time alerts.
- Title similarity deduplication uses Jaccard on trigrams; very short titles (under 5 words) may not deduplicate reliably.
- Scheduler setup requires write access to `~/Library/LaunchAgents` (macOS) or `~/.config/systemd/user/` (Linux).
- Tavily results are supplemental; the digest is fully functional without them.
- Offline operation after first fetch: `collect.py` requires network access; once a digest is written, `/news digest` reads it locally with no network required.
