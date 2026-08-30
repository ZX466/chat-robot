"""Unit tests for manager/config_manager.py."""
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import yaml

from manager.config_manager import (
    ConfigGeneratedError,
    generate_config_file,
    get_config,
    get_default_config_path,
    save_config,
    set_default_config_path,
)


@pytest.fixture(autouse=True)
def reset_globals():
    """Reset module-level globals between tests."""
    import manager.config_manager as cm
    orig_config = cm._config
    orig_custom = cm._custom_config_path
    cm._config = None
    cm._custom_config_path = None
    yield
    cm._config = orig_config
    cm._custom_config_path = orig_custom


@pytest.fixture
def tmp_config_path(tmp_path):
    return tmp_path / "resources" / "config.yaml"


# --- ConfigGeneratedError ---

@pytest.mark.unit
class TestConfigGeneratedError:
    def test_is_system_exit(self):
        assert issubclass(ConfigGeneratedError, SystemExit)

    def test_exit_code_zero(self):
        with pytest.raises(SystemExit) as exc_info:
            raise ConfigGeneratedError(0)
        assert exc_info.value.code == 0


# --- generate_config_file ---

@pytest.mark.unit
class TestGenerateConfigFile:
    def test_creates_file_and_raises(self, tmp_config_path):
        with pytest.raises(ConfigGeneratedError):
            generate_config_file(tmp_config_path)
        assert tmp_config_path.exists()

    def test_generated_file_is_valid_yaml(self, tmp_config_path):
        with pytest.raises(ConfigGeneratedError):
            generate_config_file(tmp_config_path)
        with open(tmp_config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict)

    def test_creates_parent_directory(self, tmp_path):
        single_level = tmp_path / "resources"
        with pytest.raises(ConfigGeneratedError):
            generate_config_file(single_level / "config.yaml")
        assert (single_level / "config.yaml").exists()


# --- set_default_config_path / get_default_config_path ---

@pytest.mark.unit
class TestCustomConfigPath:
    def test_custom_path_overrides_default(self, tmp_path):
        custom = tmp_path / "custom.yaml"
        set_default_config_path(custom)
        assert get_default_config_path() == custom

    @patch("manager.config_manager._custom_config_path", None)
    @patch("manager.config_manager._project_dir", Path("/fake/project"))
    def test_default_path_uses_project_dir(self):
        result = get_default_config_path()
        assert result == Path("/fake/project/resources/config.yaml")


# --- get_config ---

@pytest.mark.unit
class TestGetConfig:
    def test_raises_when_config_missing(self, tmp_path):
        missing = tmp_path / "nonexistent.yaml"
        set_default_config_path(missing)
        with pytest.raises(ConfigGeneratedError):
            get_config()

    def test_loads_valid_config(self, tmp_config_path):
        with pytest.raises(ConfigGeneratedError):
            generate_config_file(tmp_config_path)

        import manager.config_manager as cm
        cm._config = None
        config = get_config(tmp_config_path)
        assert config is not None

    def test_caches_after_first_load(self, tmp_config_path):
        with pytest.raises(ConfigGeneratedError):
            generate_config_file(tmp_config_path)

        import manager.config_manager as cm
        cm._config = None
        c1 = get_config(tmp_config_path)
        c2 = get_config(tmp_config_path)
        assert c1 is c2


# --- save_config ---

@pytest.mark.unit
class TestSaveConfig:
    def test_save_raises_on_none(self):
        with pytest.raises((ValueError, Exception)):
            save_config(None)

    def test_save_roundtrip(self, tmp_config_path):
        with pytest.raises(ConfigGeneratedError):
            generate_config_file(tmp_config_path)

        import manager.config_manager as cm
        cm._config = None
        config = get_config(tmp_config_path)
        save_config(config, tmp_config_path)

        cm._config = None
        loaded = get_config(tmp_config_path)
        assert loaded is not None
