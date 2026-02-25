"""Tests for config overlay system (preset + user overrides)."""
import textwrap
from pathlib import Path

import pytest
import yaml


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(data, f)


def _minimal_preset() -> dict:
    return {
        "feeds": [
            {"name": "Feed A", "url": "https://example.com/a.xml", "type": "rss"},
            {"name": "Feed B", "url": "https://example.com/b.xml", "type": "rss"},
        ],
        "keywords": {
            "topic_x": ["alpha", "beta"],
            "topic_y": ["gamma"],
        },
        "scoring": {"max_items": 10},
        "retention": {"seen_urls_days": 90},
    }


# ---------------------------------------------------------------------------
# load_preset
# ---------------------------------------------------------------------------

def test_load_preset(tmp_path):
    preset_data = _minimal_preset()
    preset_file = tmp_path / "test.yaml"
    _write_yaml(preset_file, preset_data)

    from pipeline.config import load_preset
    result = load_preset(preset_file)

    assert "feeds" in result
    assert len(result["feeds"]) == 2
    assert result["feeds"][0]["name"] == "Feed A"
    assert result["keywords"]["topic_x"] == ["alpha", "beta"]


# ---------------------------------------------------------------------------
# apply_overlay — add_feeds
# ---------------------------------------------------------------------------

def test_overlay_add_feeds():
    from pipeline.config import apply_overlay

    base = _minimal_preset()
    overlay = {
        "add_feeds": [
            {"name": "Feed C", "url": "https://example.com/c.xml", "type": "rss"}
        ]
    }
    result = apply_overlay(base, overlay)

    assert len(result["feeds"]) == 3
    assert result["feeds"][-1]["name"] == "Feed C"
    # original must not be mutated
    assert len(base["feeds"]) == 2


# ---------------------------------------------------------------------------
# apply_overlay — remove_feeds
# ---------------------------------------------------------------------------

def test_overlay_remove_feeds():
    from pipeline.config import apply_overlay

    base = _minimal_preset()
    overlay = {"remove_feeds": ["Feed A"]}
    result = apply_overlay(base, overlay)

    names = [f["name"] for f in result["feeds"]]
    assert "Feed A" not in names
    assert "Feed B" in names
    # original must not be mutated
    assert len(base["feeds"]) == 2


# ---------------------------------------------------------------------------
# apply_overlay — add_keywords
# ---------------------------------------------------------------------------

def test_overlay_add_keywords():
    from pipeline.config import apply_overlay

    base = _minimal_preset()
    overlay = {"add_keywords": {"topic_z": ["delta", "epsilon"]}}
    result = apply_overlay(base, overlay)

    assert "topic_z" in result["keywords"]
    assert result["keywords"]["topic_z"] == ["delta", "epsilon"]
    # existing topics intact
    assert "topic_x" in result["keywords"]
    # original must not be mutated
    assert "topic_z" not in base["keywords"]


# ---------------------------------------------------------------------------
# apply_overlay — remove_keywords
# ---------------------------------------------------------------------------

def test_overlay_remove_keywords():
    from pipeline.config import apply_overlay

    base = _minimal_preset()
    overlay = {"remove_keywords": ["topic_x"]}
    result = apply_overlay(base, overlay)

    assert "topic_x" not in result["keywords"]
    assert "topic_y" in result["keywords"]
    # original must not be mutated
    assert "topic_x" in base["keywords"]


# ---------------------------------------------------------------------------
# apply_overlay — max_items override
# ---------------------------------------------------------------------------

def test_overlay_max_items_override():
    from pipeline.config import apply_overlay

    base = _minimal_preset()
    overlay = {"max_items": 25}
    result = apply_overlay(base, overlay)

    assert result["scoring"]["max_items"] == 25
    # original must not be mutated
    assert base["scoring"]["max_items"] == 10


# ---------------------------------------------------------------------------
# resolve_config — preset only (no user config file)
# ---------------------------------------------------------------------------

def test_resolve_config_preset_only(tmp_path, monkeypatch):
    # Point XDG_CONFIG_HOME to a dir without a config.yaml
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))

    preset_dir = tmp_path / "presets"
    preset_dir.mkdir()
    preset_data = _minimal_preset()
    _write_yaml(preset_dir / "ai-engineering.yaml", preset_data)

    from pipeline.config import resolve_config
    result = resolve_config(preset_dir=preset_dir, preset_name="ai-engineering")

    assert len(result["feeds"]) == 2
    assert result["scoring"]["max_items"] == 10


# ---------------------------------------------------------------------------
# resolve_config — user config overlays preset
# ---------------------------------------------------------------------------

def test_resolve_config_with_overlay(tmp_path, monkeypatch):
    cfg_dir = tmp_path / "cfg" / "claude-news"
    cfg_dir.mkdir(parents=True)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))

    preset_dir = tmp_path / "presets"
    preset_dir.mkdir()
    preset_data = _minimal_preset()
    _write_yaml(preset_dir / "ai-engineering.yaml", preset_data)

    user_config = {
        "preset": "ai-engineering",
        "add_feeds": [{"name": "Feed C", "url": "https://example.com/c.xml", "type": "rss"}],
        "remove_feeds": ["Feed A"],
        "max_items": 20,
    }
    _write_yaml(cfg_dir / "config.yaml", user_config)

    from pipeline.config import resolve_config
    result = resolve_config(preset_dir=preset_dir)

    names = [f["name"] for f in result["feeds"]]
    assert "Feed A" not in names
    assert "Feed B" in names
    assert "Feed C" in names
    assert result["scoring"]["max_items"] == 20


# ---------------------------------------------------------------------------
# resolve_config — blank preset
# ---------------------------------------------------------------------------

def test_resolve_config_rejects_path_traversal(tmp_path, monkeypatch):
    cfg_dir = tmp_path / "cfg" / "claude-news"
    cfg_dir.mkdir(parents=True)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))

    preset_dir = tmp_path / "presets"
    preset_dir.mkdir()

    from pipeline.config import resolve_config
    with pytest.raises(ValueError, match="Invalid preset name"):
        resolve_config(preset_dir=preset_dir, preset_name="../../etc/passwd")


def test_resolve_config_blank(tmp_path, monkeypatch):
    cfg_dir = tmp_path / "cfg" / "claude-news"
    cfg_dir.mkdir(parents=True)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))

    user_config = {
        "preset": "blank",
        "add_feeds": [{"name": "My Feed", "url": "https://example.com/mine.xml", "type": "rss"}],
        "add_keywords": {"custom": ["foo", "bar"]},
    }
    _write_yaml(cfg_dir / "config.yaml", user_config)

    from pipeline.config import resolve_config
    result = resolve_config()

    assert len(result["feeds"]) == 1
    assert result["feeds"][0]["name"] == "My Feed"
    assert result["keywords"] == {"custom": ["foo", "bar"]}
    assert result["scoring"]["max_items"] == 10
