"""Application config loading."""

from pathlib import Path
from typing import NamedTuple, Dict

from confinator.validation import ValidConfig

_PKG_ROOT = Path(__file__).parent

USER_CONFIG_PATH = Path.home() / ".config/confinator/example_app/config"
SCHEMA_PATH = _PKG_ROOT / "schema"


class FooConfig(NamedTuple):
    bar: int
    baz: Dict[str, bool]


class BooConfig(NamedTuple):
    bar: int


class AppConfig(NamedTuple):
    foo: FooConfig
    boo: BooConfig


def _load_config() -> AppConfig:
    config = ValidConfig(config_file=USER_CONFIG_PATH, schema_file=SCHEMA_PATH)

    return AppConfig(
        foo=FooConfig(
            bar=config.getint(section="foo", option="bar", fallback=0),
            baz={
                option[4:]: config.getboolean(section="foo", option=option)
                for option in config.options("foo")
                if option.startswith("baz_")
            },
        ),
        boo=BooConfig(bar=config.getint(section="boo", option="bar", fallback=0)),
    )


conf = _load_config()
