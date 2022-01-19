"""Command line interface tool for INI style config files."""

from __future__ import annotations

import argparse
import logging
import os
import re
import subprocess
import sys
from configparser import NoSectionError, NoOptionError
from pathlib import Path
from typing import NamedTuple, Union

from .validation import ValidConfig, InvalidConfigError

_log = logging.getLogger(__name__)


class _SectionOption(NamedTuple):
    """Represents the section and name of an option."""

    section: str
    option: str

    @classmethod
    def from_dot_notation(cls, name: str) -> _SectionOption:
        """Parse the passed option into section and option name.

        Args:
            name: name of the option together with the section in the format of SECTION.OPTION

        Returns:
            SectionOption object

        Raises:
            ValueError: if the passed name is not matching the expected format
        """
        try:
            return cls(**re.match(r"^(?P<section>\w+)\.(?P<option>\w+)$", name).groupdict())
        except AttributeError:
            raise ValueError(f"Invalid name format. Valid format is 'section.option', but got '{name}'.")


class ConfigCLI(ValidConfig):
    """CLI for config file."""

    def __init__(self, config_file: Union[Path, str], schema_file: Union[Path, str], **kwargs) -> None:
        """Init config parser.

        Args:
            config_file: path to the config file
            schema_file: path to a config file for validation
            **kwargs: various keyword arguments that will be passed to the underlying ConfigParser initialization
        """
        super().__init__(config_file=config_file, schema_file=schema_file, **kwargs)

        self._config_file = Path(config_file)
        self._schema_file = Path(schema_file)

    def _validate(self) -> None:
        try:
            super()._validate()
        except InvalidConfigError as e:
            _log.error(e)
            sys.exit(1)

    def _get_arg_parser(self) -> argparse.ArgumentParser:
        """Create argument parser with required arguments."""
        parser = argparse.ArgumentParser(
            description=f"Get and set options in the config file located at {self._config_file}",
            usage=f"%(prog)s [-h | name | name value | -l | -e | --unset NAME | --unset-all | --list-valid-options]",
        )

        parser.add_argument(
            "name", nargs="?", help="Name of the config parameter to get or set in 'section.option' format."
        )
        parser.add_argument("value", nargs="?", help="Value of the config parameter to set.")

        action_group = parser.add_argument_group("Actions")
        mxg_action_group = action_group.add_mutually_exclusive_group()
        mxg_action_group.add_argument(
            "-l", "--list", action="store_true", help="List all variables set in the config file."
        )
        mxg_action_group.add_argument(
            "-e", "--edit", action="store_true", help="Opens the config file with the default editor."
        )
        mxg_action_group.add_argument(
            "--unset", dest="unset_name", metavar="NAME", help="Remove a variable by name from the config file."
        )
        mxg_action_group.add_argument(
            "--unset-all", action="store_true", help="Remove all variables from the config file."
        )
        mxg_action_group.add_argument(
            "--list-valid-options", action="store_true", help="List the valid section, option and value formats."
        )

        return parser

    def run(self) -> None:
        """Parse command line arguments and run required action accordingly."""
        parser = self._get_arg_parser()
        args = parser.parse_args()

        if args.name:
            if any([args.unset_name, args.unset_all, args.list, args.edit, args.list_valid_options]):
                parser.error("Positional arguments and actions are not allowed together!")
            try:
                parts = _SectionOption.from_dot_notation(args.name)
            except ValueError as e:
                _log.error(e)
                sys.exit(2)
            if args.value:
                self._set_option(parts.section, parts.option, args.value)
            else:
                self._get_option(parts.section, parts.option)

        elif args.unset_name:
            try:
                parts = _SectionOption.from_dot_notation(args.unset_name)
            except ValueError as e:
                _log.error(e)
                sys.exit(2)
            self._unset_option(parts.section, parts.option)

        elif args.unset_all:
            self._unset_all()

        elif args.list:
            self._list()

        elif args.list_valid_options:
            self._print_valid_config()

        elif args.edit:
            self._edit()

        else:
            parser.print_help()

    def _set_option(self, section: str, option: str, value: str) -> None:
        """Set option value or add new option."""
        if not self.has_section(section):
            self.add_section(section)
        self.set(section, option, value)
        self.save()

    def _get_option(self, section: str, option: str) -> None:
        """Print the value of the option to stdout."""
        try:
            print(self.get(section, option))
        except (NoSectionError, NoOptionError) as e:
            _log.error(e)
            sys.exit(1)

    def _unset_option(self, section: str, option: str) -> None:
        """Unset the passed option.

        Also remove the section if this was the last option there.
        """
        try:
            if not self.remove_option(section, option):
                pass
            else:
                if not self.options(section):
                    self.remove_section(section)
                self.save()
        except NoSectionError as e:
            _log.error(e)
            sys.exit(1)

    def _unset_all(self) -> None:
        """Unset all variables."""
        for section in self.sections():
            self.remove_section(section)
        self.save()

    def _list(self) -> None:
        """List all variables set in the config."""
        for section in self.sections():
            for option in self.options(section):
                print(f"{section}.{option}={self.get(section, option)}")

    def _print_valid_config(self):
        """Print the content of the schema file to stdout."""
        with self._schema_file.open() as f:
            print(f.read())

    def _edit(self) -> None:
        """Opens an editor to modify the specified config file.

        Try to use the preferred editor by first looking the VISUAL and then the EDITOR environment variables. If none
        of them are set or they are empty, then use vim.
        """
        editor = os.getenv("VISUAL") or os.getenv("EDITOR") or "vim"
        subprocess.run([editor, self._config_file])
