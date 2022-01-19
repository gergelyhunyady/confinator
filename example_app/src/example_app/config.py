"""Application config loading."""

from pathlib import Path

_DEFAULT_CONFIG_PATH = Path(__file__).parent / "config_files/default"
USER_CONFIG_PATH = Path.home() / ".config/confinator/example_app_config"
SCHEMA_CONFIG_PATH = Path(__file__).parent / "config_files/schema"
