"""Tests for XDG path resolution."""


def test_config_dir_default(tmp_path, monkeypatch):
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    from pipeline.paths import config_dir
    assert config_dir() == tmp_path / ".config" / "claude-news"


def test_config_dir_xdg_override(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "custom"))
    from pipeline.paths import config_dir
    assert config_dir() == tmp_path / "custom" / "claude-news"


def test_data_dir_default(tmp_path, monkeypatch):
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    from pipeline.paths import data_dir
    assert data_dir() == tmp_path / ".local" / "share" / "claude-news"


def test_data_dir_xdg_override(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    from pipeline.paths import data_dir
    assert data_dir() == tmp_path / "data" / "claude-news"


def test_venv_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    from pipeline.paths import venv_dir
    assert venv_dir() == tmp_path / "claude-news" / ".venv"


def test_config_file(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    from pipeline.paths import config_file
    assert config_file() == tmp_path / "claude-news" / "config.yaml"


def test_digests_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    from pipeline.paths import digests_dir
    assert digests_dir() == tmp_path / "claude-news" / "data" / "digests"


def test_raw_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    from pipeline.paths import raw_dir
    assert raw_dir() == tmp_path / "claude-news" / "data" / "raw"


def test_state_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    from pipeline.paths import state_dir
    assert state_dir() == tmp_path / "claude-news" / "data" / "state"
