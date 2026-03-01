# Herald — Reference

## Commands

### `/news init [topic]`

Bootstraps Herald for the current environment. Creates `~/.config/herald/config.yaml` if it does not exist, installs the scheduler, and runs an immediate first fetch so a digest is available before the next scheduled run.

If `topic` is provided, that topic pack is loaded as the primary source set. If omitted, the default `ai-engineering` preset is used.

**Built-in topic packs**

| Pack | Coverage |
|------|----------|
| `ai-engineering` | HN, Simon Willison, AlphaSignal, HF Papers, arXiv, and 15 additional feeds across 5 tiers |
| `rust` | This Week in Rust, Rust blog, r/rust, crates.io releases |
| `devops` | DevOps Weekly, SRE Weekly, Kubernetes blog, CNCF |
| `golang` | Go blog, Golang Weekly, r/golang |
| `typescript` | TypeScript blog, TC39 proposals, JS Weekly |
| `security` | Krebs, Schneier, CISA advisories, CVE feeds |
| `python` | Python Insider, PyPI releases, PyCoder's Weekly |
| `data` | Data Elixir, Towards Data Science, DuckDB blog |

**Examples**
```
/news init
/news init rust
/news init security
```

---

### `/news add <url|topic>`

Adds a single RSS/Atom feed URL or an entire topic pack to the existing configuration. Does not restart the scheduler or run a fetch. The new source will be included in the next scheduled or manual run.

**Examples**
```
/news add https://blog.example.com/feed.xml
/news add golang
/news add https://simonwillison.net/atom/everything/
```

**Note:** Adding a topic pack that is already partially configured merges the new feeds without duplicating existing ones.

---

### `/news sources`

Lists all configured feed sources with their topic group, tier weight, and the timestamp of the last successful fetch. Useful for verifying what will be included in the next digest.

**Output example**
```
ai-engineering (20 sources)
  [tier-1] Hacker News (Algolia API)         last: 2026-03-01 07:03
  [tier-1] Simon Willison                    last: 2026-03-01 07:03
  [tier-2] AlphaSignal                       last: 2026-03-01 07:04
  [tier-2] Hugging Face Papers               last: 2026-03-01 07:04
  [tier-3] arXiv cs.AI                       last: 2026-03-01 07:05
  ...
```

---

### `/news digest`

Reads and displays today's digest. If today's digest file does not yet exist (e.g., the scheduler has not run yet today), Herald runs an on-demand fetch before displaying results.

**Output format**

```
Herald Digest — 2026-03-01
══════════════════════════

[ai-engineering] Top stories

1. "Title of story one" — Source Name
   HN: 342 pts | 87 comments | https://...

2. "Title of story two" — Source Name
   https://...

...

[rust] Top stories

1. ...
```

**Example**
```
/news digest
```

---

### `/news run`

Triggers an immediate fetch-and-analyze cycle outside the normal schedule. Useful after adding new sources or when you want a mid-day refresh. Respects the lockfile — if a scheduled run is in progress, this command waits or exits cleanly.

**Example**
```
/news run
```

---

### `/news stop`

Uninstalls the scheduler (removes the launchd plist or systemd unit). Does not delete configuration or digest data. Run `/news init` again to re-enable scheduled fetching.

**Example**
```
/news stop
```

---

## Skill: `news-digest`

Activates automatically when the conversation contains any of the following phrases:
- "what's new"
- "latest trends"
- "today's news"
- "what happened in [topic]"
- "recent updates"

When triggered, the skill reads the most recent available digest (today's if it exists, otherwise yesterday's) and inserts a formatted summary inline. No network call is made by the skill.

---

## Configuration

Configuration file: `~/.config/herald/config.yaml`

The file is an overlay on top of the immutable preset. Only specify values you want to change.

```yaml
# Optional: Tavily API key for extended search
tavily_api_key: ""  # or set TAVILY_API_KEY env var

# Schedule (cron syntax)
schedule: "0 7 * * *"  # 07:00 daily

# Digest retention (days)
retention_days: 30

# Per-run item cap
top_n: 10

# Custom feeds (merged with preset)
feeds:
  - url: https://blog.example.com/feed.xml
    topic: custom
    tier: 3
    keywords:
      - rust
      - async

# Keyword overrides (merged with preset topic keywords)
keywords:
  ai-engineering:
    - agents
    - MCP
    - "context window"
```

**Immutable preset location:** bundled inside the Herald package. Do not edit directly — it will be overwritten on upgrade. Use `~/.config/herald/config.yaml` for all customizations.

---

## Source Tier Weights

The scoring formula uses a tier weight as the base score for each item:

| Tier | Weight | Typical sources |
|------|--------|-----------------|
| 1 | 3.0 | HN front page, curated newsletters (Simon Willison, AlphaSignal) |
| 2 | 2.0 | Official blogs (HF, arXiv, Rust blog), major aggregators |
| 3 | 1.0 | Community subreddits, personal blogs, secondary feeds |
| 4 | 0.5 | High-volume feeds, less curated |

---

## Data Locations

| Purpose | Path |
|---------|------|
| User configuration | `~/.config/herald/config.yaml` |
| Raw fetched items | `~/.local/share/herald/raw/YYYY-MM-DD.jsonl` |
| Digests | `~/.local/share/herald/digests/YYYY-MM-DD.yaml` |
| Fetch log | `~/.local/share/herald/herald.log` |
| Lock file | `/tmp/herald.lock` |
| launchd plist (macOS) | `~/Library/LaunchAgents/dev.skill7.herald.plist` |
| systemd unit (Linux) | `~/.config/systemd/user/herald.service` |

---

## Troubleshooting

**No digest appears after init**
The first fetch runs synchronously during `/news init`. If it silently produced no items, check `~/.local/share/herald/herald.log` for errors. Common causes: network timeout, all feeds returned non-200, JSONL write permission issue.

**"herald.lock exists, another run in progress"**
A previous run may have crashed without releasing the lock. If no fetch process is running (`ps aux | grep herald`), delete `/tmp/herald.lock` manually and retry.

**Scheduler not running (macOS)**
Verify the plist is loaded: `launchctl list | grep herald`. If absent, run `/news init` again. If present but not firing, check `~/Library/LaunchAgents/dev.skill7.herald.plist` for syntax errors with `plutil -lint`.

**Scheduler not running (Linux)**
Check the unit status: `systemctl --user status herald.timer`. If inactive, run `systemctl --user enable --now herald.timer`. If systemd is not available, verify the cron entry with `crontab -l`.

**Digest is stale (yesterday's date)**
The scheduler may not have fired. Run `/news run` for an immediate fetch. Check the log: `tail -50 ~/.local/share/herald/herald.log`.

**Tavily results not appearing**
Ensure `TAVILY_API_KEY` is set in the environment where Herald runs (the scheduler environment, not just your interactive shell). Add it to `~/.config/herald/config.yaml` under `tavily_api_key` as an alternative.

**Duplicate stories in digest**
Title similarity deduplication has a 0.85 Jaccard threshold. Very short or heavily abbreviated titles may not match. You can add feed URLs to a `blocklist` in `config.yaml` to exclude high-duplication sources:
```yaml
blocklist:
  - https://feeds.example.com/noisy-feed.rss
```

**Feed fetch error: 10 MB limit exceeded**
A feed is returning an unusually large payload. Add it to the blocklist or contact the feed provider.
