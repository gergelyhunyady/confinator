"""Module foo of ExampleApp."""

from .config import conf


def conf_printer() -> None:
    print(conf.foo)
