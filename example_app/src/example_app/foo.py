"""Module foo of ExampleApp."""

from .config import conf


def foo_conf_printer(args) -> None:
    print(conf.foo)
