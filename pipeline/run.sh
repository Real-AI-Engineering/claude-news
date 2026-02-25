#!/usr/bin/env bash
# run.sh — orchestrate collection + analysis with lockfile + atomic writes
# Designed for XDG paths: config from ~/.config/claude-news/, data in ~/.local/share/claude-news/
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_DIR="$(dirname "$SCRIPT_DIR")"
DATE=$(date +%Y-%m-%d)

# Resolve XDG paths
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/claude-news"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/claude-news"

# Ensure directories exist
mkdir -p "$DATA_DIR/data/state" "$DATA_DIR/data/raw" "$DATA_DIR/data/digests"

LOCKFILE="$DATA_DIR/data/state/run.lock"
LOG="$DATA_DIR/data/state/collect.log"
VENV="$DATA_DIR/.venv"

# Load .env if present (launchd/systemd don't inherit shell env)
ENV_FILE="$CONFIG_DIR/.env"
if [ -f "$ENV_FILE" ]; then
    set -a
    # shellcheck source=/dev/null
    source "$ENV_FILE"
    set +a
fi

# Verify venv exists
if [ ! -f "$VENV/bin/activate" ]; then
    echo "$(date -Iseconds) ERROR: venv not found at $VENV. Run /news init first." >> "$LOG"
    exit 1
fi

# Lockfile — prevent duplicate runs (mkdir = portable POSIX atomic lock)
if ! mkdir "$LOCKFILE.d" 2>/dev/null; then
    echo "$(date -Iseconds) SKIP: another run in progress" >> "$LOG"
    exit 0
fi
trap 'rmdir "$LOCKFILE.d" 2>/dev/null' EXIT

# Activate venv
# shellcheck source=/dev/null
source "$VENV/bin/activate"

# Helper: filter API keys from stderr
filter_log() {
    sed -E 's/(sk-[a-zA-Z0-9_-]{10})[a-zA-Z0-9_-]*/\1**REDACTED**/g; s/(tvly-[a-zA-Z0-9_-]{10})[a-zA-Z0-9_-]*/\1**REDACTED**/g'
}

echo "$(date -Iseconds) START collect" >> "$LOG"

# Write last_run.json (started)
cat > "$DATA_DIR/data/state/last_run.json" <<LASTRUN
{"timestamp": "$(date -Iseconds)", "status": "running", "items_collected": 0, "items_kept": 0}
LASTRUN

# Phase 1: Collect
RAW_FILE="$DATA_DIR/data/raw/$DATE.jsonl"
PYTHONPATH="$PLUGIN_DIR" python3 "$SCRIPT_DIR/collect.py" \
    --config "$CONFIG_DIR/config.yaml" \
    --output "$RAW_FILE" \
    2> >(filter_log >> "$LOG") || {
    echo "$(date -Iseconds) ERROR: collect.py failed" >> "$LOG"
}

# Phase 2: Analyze (only if raw file exists and non-empty)
if [ -s "$RAW_FILE" ]; then
    # JSONL integrity check
    if ! python3 -c "import json, sys; [json.loads(l) for l in open(sys.argv[1]) if l.strip()]" "$RAW_FILE" 2>/dev/null; then
        echo "$(date -Iseconds) WARN: corrupt JSONL, attempting partial recovery" >> "$LOG"
        python3 -c "
import json, sys
with open(sys.argv[1]) as f:
    lines = f.readlines()
valid = [l for l in lines if l.strip()]
good = []
for l in valid:
    try:
        json.loads(l)
        good.append(l)
    except json.JSONDecodeError:
        pass
with open(sys.argv[1], 'w') as f:
    f.writelines(good)
print(f'Recovered {len(good)}/{len(valid)} lines')
" "$RAW_FILE" >> "$LOG" 2>&1
    fi

    PYTHONPATH="$PLUGIN_DIR" python3 "$SCRIPT_DIR/analyze.py" \
        --config "$CONFIG_DIR/config.yaml" \
        --input "$RAW_FILE" \
        --output "$DATA_DIR/data/digests/$DATE.md" \
        --state-dir "$DATA_DIR/data/state" \
        2> >(filter_log >> "$LOG") || {
        echo "$(date -Iseconds) ERROR: analyze.py failed" >> "$LOG"
    }
else
    echo "$(date -Iseconds) SKIP: no raw data for $DATE" >> "$LOG"
fi

# Update last_run.json
COLLECTED=$(wc -l < "$RAW_FILE" 2>/dev/null | tr -d ' ' || echo 0)
DIGEST_FILE="$DATA_DIR/data/digests/$DATE.md"
if [ -f "$DIGEST_FILE" ]; then
    # Extract "Kept: N" from digest stats line
    KEPT=$(grep -oP 'Kept: \K[0-9]+' "$DIGEST_FILE" 2>/dev/null || echo 0)
else
    KEPT=0
fi
cat > "$DATA_DIR/data/state/last_run.json" <<LASTRUN
{"timestamp": "$(date -Iseconds)", "status": "success", "items_collected": $COLLECTED, "items_kept": $KEPT}
LASTRUN

# Cleanup: prune old data per retention policy
find "$DATA_DIR/data/raw" -name "*.jsonl" -mtime +90 -delete 2>/dev/null || true
find "$DATA_DIR/data/digests" -name "*.md" -mtime +365 -delete 2>/dev/null || true

echo "$(date -Iseconds) DONE" >> "$LOG"
