"""Module boo of ExampleApp."""

from .config import conf


def boo_conf_printer(args) -> None:
    print(conf.boo)
