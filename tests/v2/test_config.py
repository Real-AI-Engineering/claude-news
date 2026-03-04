from __future__ import annotations

from herald.config import load_config_from_string, HeraldConfig, ClusterConfig


def test_load_minimal():
    cfg = load_config_from_string("")
    assert isinstance(cfg, HeraldConfig)
    assert cfg.sources == []
    assert cfg.clustering.threshold == 0.65
    assert cfg.schedule.interval_hours == 4


def test_load_sources():
    yaml_str = """
sources:
  - id: hn
    name: Hacker News
    weight: 0.3
    category: community
  - id: rss1
    name: Simon Willison
    url: https://simonwillison.net/atom/everything/
"""
    cfg = load_config_from_string(yaml_str)
    assert len(cfg.sources) == 2
    assert cfg.sources[0].id == "hn"
    assert cfg.sources[0].weight == 0.3
    assert cfg.sources[1].url == "https://simonwillison.net/atom/everything/"


def test_source_defaults():
    yaml_str = """
sources:
  - id: test
    name: Test Source
"""
    cfg = load_config_from_string(yaml_str)
    assert cfg.sources[0].weight == 0.2
    assert cfg.sources[0].category == "community"
    assert cfg.sources[0].url is None


def test_clustering_params():
    yaml_str = """
clustering:
  threshold: 0.8
  max_time_gap_days: 3
"""
    cfg = load_config_from_string(yaml_str)
    assert cfg.clustering.threshold == 0.8
    assert cfg.clustering.max_time_gap_days == 3
    assert cfg.clustering.min_title_words == 4  # default
    assert cfg.clustering.canonical_delta == 0.1  # default


def test_clustering_defaults():
    cfg = load_config_from_string("")
    assert cfg.clustering == ClusterConfig()


def test_schedule():
    yaml_str = """
schedule:
  interval_hours: 8
"""
    cfg = load_config_from_string(yaml_str)
    assert cfg.schedule.interval_hours == 8


def test_topics():
    yaml_str = """
topics:
  ai_agents:
    - agent
    - mcp
  ai_models:
    - llm
    - gpt
"""
    cfg = load_config_from_string(yaml_str)
    assert "ai_agents" in cfg.topics
    assert cfg.topics["ai_agents"] == ["agent", "mcp"]


def test_full_config():
    yaml_str = """
sources:
  - id: hn
    name: Hacker News
    weight: 0.3
    category: community
clustering:
  threshold: 0.7
schedule:
  interval_hours: 6
topics:
  test:
    - keyword1
"""
    cfg = load_config_from_string(yaml_str)
    assert len(cfg.sources) == 1
    assert cfg.clustering.threshold == 0.7
    assert cfg.schedule.interval_hours == 6
    assert cfg.topics["test"] == ["keyword1"]
