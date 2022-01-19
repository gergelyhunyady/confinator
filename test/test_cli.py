#!/usr/bin/env python3
"""Test the cli module."""

import argparse
import os
import sys
import unittest
from configparser import ConfigParser, NoSectionError, NoOptionError
from io import StringIO
from os.path import basename
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock, create_autospec, call

from confinator.cli import ConfigCLI, _SectionOption
from confinator.validation import InvalidConfigError

EXPECTED_HELP_MSG = f"""\
usage: {basename(sys.argv[0])} [-h | name | name value | -l | -e | --unset NAME | --unset-all | --list-valid-options]

Get and set options in the config file located at /some/test/path

positional arguments:
  name                  Name of the config parameter to get or set in
                        'section.option' format.
  value                 Value of the config parameter to set.

optional arguments:
  -h, --help            show this help message and exit

Actions:
  -l, --list            List all variables set in the config file.
  -e, --edit            Opens the config file with the default editor.
  --unset NAME          Remove a variable by name from the config file.
  --unset-all           Remove all variables from the config file.
  --list-valid-options  List the valid section, option and value formats.
"""


class TestSectionOption(unittest.TestCase):
    """Test the _SectionOption class."""

    def test_from_dot_notation_with_correct_name(self) -> None:
        """Test the from_dot_notation method with correct name passed.

        GIVEN a string containing one dot char inside (not the front or end).
        WHEN calling the from_dot_notation method of the _SectionOption class with this string,
        THEN it should return a _SectionOption instance with 2 attributes (section and option)
                holding the first part and the second part respectively of the string split at the dot.
        """
        # Setup environment.
        test_name = "section_name.option_name"

        # Run.
        parts = _SectionOption.from_dot_notation(test_name)

        # Assert.
        self.assertEqual(parts.section, "section_name")
        self.assertEqual(parts.option, "option_name")

    def test_from_dot_notation_with_incorrect_name(self) -> None:
        """Test the from_dot_notation method with incorrect name passed.

        GIVEN a string containing no dot char or one dot char on one of the end or more than one dot.
        WHEN calling the from_dot_notation method of the _SectionOption class with this string,
        THEN it should raise ValueError with proper message.
        """
        # Setup environment.
        test_names = ["some_string", ".some_string", "some_string.", "some.bad.string"]

        # Run and assert.
        for test_name in test_names:
            with self.subTest(test_name=test_name):
                with self.assertRaises(ValueError) as cm:
                    _SectionOption.from_dot_notation(test_name)
                self.assertEqual(
                    str(cm.exception), f"Invalid name format. Valid format is 'section.option', but got '{test_name}'."
                )


class TestCLIConfigInit(unittest.TestCase):
    """Test the initialization of the ConfigCLI class."""

    @patch("confinator.cli.ValidConfig.__init__")
    def test_init(self, mock_parent_init: MagicMock) -> None:
        """Test the __init__ method of the ConfigCLI.

        GIVEN a string path representing the config file,
            AND another string path representing the valid config file,
        WHEN instantiating a ConfigCLI object with them and with some extra arguments,
        THEN the __init__ method of the parent class should be called with the correct arguments,
            AND the _config_file attribute of the created instance should be the first path converted to pathlib Path,
            AND the _schema_file attribute of the created instance should be the second path converted to pathlib Path.
        """
        # Setup environment.
        mock_config_file = "/some/test/path"
        mock_schema_file = "/some/different/test/path"
        first, second = Mock(), Mock()

        # Run.
        config = ConfigCLI(config_file=mock_config_file, schema_file=mock_schema_file, first=first, second=second)

        # Assert.
        mock_parent_init.assert_called_once_with(
            config_file=mock_config_file, schema_file=mock_schema_file, first=first, second=second
        )
        self.assertEqual(config._config_file, Path(mock_config_file))
        self.assertEqual(config._schema_file, Path(mock_schema_file))


class TestCLIConfig(unittest.TestCase):
    """Test the different methods of the ConfigCLI class."""

    @patch.object(ConfigCLI, "__init__", lambda *_: None)
    def setUp(self) -> None:
        """Common initialization code for all tests."""
        self.mock_config = ConfigCLI()
        self.maxDiff = None

    @patch("confinator.cli.ValidConfig._validate")
    def test_validate(self, mock_parent_validate: MagicMock) -> None:
        """Test the _validate method

        GIVEN a ConfigCLI object
        WHEN calling its _validate method
        THEN it should call the parents _validate method
            AND raise SystemExit if InvalidConfigError is encountered
        """
        # should not raise SysExit
        self.mock_config._validate()

        # setup env
        mock_parent_validate.side_effect = InvalidConfigError
        # run and assert
        with self.assertRaises(SystemExit) as cm, patch("sys.stderr", new_callable=StringIO):
            self.mock_config._validate()
        self.assertEqual(cm.exception.code, 1)

    def test_get_arg_parser(self) -> None:
        """Test the _get_arg_parser method.

        GIVEN a ConfigCLI object,
            AND its _config_file attribute is a pathlib Path instance,
            AND its _schema attribute is a ConfigParser instance.
        WHEN calling the _get_arg_parser method on the ConfigCLI object
        THEN it should return an argparse.ArgumentParser object that parses the arguments as expected,
            AND the help message generated by the parser should match the expected format.
        """
        # Setup environment.
        self.mock_config._config_file = Path("/some/test/path")
        self.mock_config._schema = ConfigParser()

        # Run.
        parser = self.mock_config._get_arg_parser()

        # Assert.
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            parser.print_help()
            self.assertEqual(mock_stdout.getvalue(), EXPECTED_HELP_MSG)

        args = parser.parse_args([])
        self.assertDictEqual(
            vars(args),
            {
                "edit": False,
                "list": False,
                "name": None,
                "unset_all": False,
                "unset_name": None,
                "value": None,
                "list_valid_options": False,
            },
        )

        args = parser.parse_args(["section_name.option_name"])
        self.assertDictEqual(
            vars(args),
            {
                "edit": False,
                "list": False,
                "name": "section_name.option_name",
                "unset_all": False,
                "unset_name": None,
                "value": None,
                "list_valid_options": False,
            },
        )

        args = parser.parse_args(["section_name.option_name", "option_value"])
        self.assertDictEqual(
            vars(args),
            {
                "edit": False,
                "list": False,
                "name": "section_name.option_name",
                "unset_all": False,
                "unset_name": None,
                "value": "option_value",
                "list_valid_options": False,
            },
        )

        with self.assertRaises(SystemExit) as cm, patch("sys.stderr", new_callable=StringIO):
            parser.parse_args(["section_name", "option_name", "option_value"])
        self.assertEqual(cm.exception.code, 2)

        args = parser.parse_args(["-e"])
        self.assertDictEqual(
            vars(args),
            {
                "edit": True,
                "list": False,
                "name": None,
                "unset_all": False,
                "unset_name": None,
                "value": None,
                "list_valid_options": False,
            },
        )

        args = parser.parse_args(["-l"])
        self.assertDictEqual(
            vars(args),
            {
                "edit": False,
                "list": True,
                "name": None,
                "unset_all": False,
                "unset_name": None,
                "value": None,
                "list_valid_options": False,
            },
        )

        args = parser.parse_args(["--unset", "section_name.option_name"])
        self.assertDictEqual(
            vars(args),
            {
                "edit": False,
                "list": False,
                "name": None,
                "unset_all": False,
                "unset_name": "section_name.option_name",
                "value": None,
                "list_valid_options": False,
            },
        )

        args = parser.parse_args(["--unset-all"])
        self.assertDictEqual(
            vars(args),
            {
                "edit": False,
                "list": False,
                "name": None,
                "unset_all": True,
                "unset_name": None,
                "value": None,
                "list_valid_options": False,
            },
        )

        args = parser.parse_args(["--list-valid-options"])
        self.assertDictEqual(
            vars(args),
            {
                "edit": False,
                "list": False,
                "name": None,
                "unset_all": False,
                "unset_name": None,
                "value": None,
                "list_valid_options": True,
            },
        )

        with self.assertRaises(SystemExit) as cm, patch("sys.stderr", new_callable=StringIO):
            parser.parse_args(["-l", "--unset", "section_name.option_name"])
        self.assertEqual(cm.exception.code, 2)

    @patch.object(ConfigCLI, "_get_option")
    @patch.object(ConfigCLI, "_get_arg_parser")
    def test_run_with_name_only(self, mock_get_arg_parser: MagicMock, mock_get_option: MagicMock) -> None:
        """Test the run method when only one positional argument is passed.

        GIVEN a ConfigCLI object,
            AND the _get_arg_parser method of this object returns an argparse.ArgumentParser object
            AND calling the parse_args method on this returns an argparse.Namespace object with only the name argument
                being not the default.
        WHEN calling the run method on the ConfigCLI object
        THEN the _get_option method of this same object should be called once with the correct args.
        """
        # Setup environment.
        mock_parser = create_autospec(argparse.ArgumentParser)
        args = argparse.Namespace(
            name="section_name.option_name",
            value=None,
            unset_name=None,
            list=False,
            edit=False,
            unset_all=False,
            list_valid_options=False,
        )
        mock_parser.parse_args.return_value = args
        mock_get_arg_parser.return_value = mock_parser

        # Run.
        self.mock_config.run()

        # Assert.
        mock_get_arg_parser.assert_called_once_with()
        mock_get_option.assert_called_once_with("section_name", "option_name")

    @patch.object(ConfigCLI, "_set_option")
    @patch.object(ConfigCLI, "_get_arg_parser")
    def test_run_with_name_and_value(self, mock_get_arg_parser: MagicMock, mock_set_option: MagicMock) -> None:
        """Test the run method when two positional arguments are passed.

        GIVEN a ConfigCLI object,
            AND the _get_arg_parser method of this object returns an argparse.ArgumentParser object
            AND calling the parse_args method on this returns an argparse.Namespace object with the name and value
                arguments being not the default.
        WHEN calling the run method on the ConfigCLI object
        THEN the _set_option method of this same object should be called once with the correct args.
        """
        # Setup environment.
        mock_parser = create_autospec(argparse.ArgumentParser)
        args = argparse.Namespace(
            name="section_name.option_name",
            value="option_value",
            unset_name=None,
            list=False,
            edit=False,
            unset_all=False,
            list_valid_options=False,
        )
        mock_parser.parse_args.return_value = args
        mock_get_arg_parser.return_value = mock_parser

        # Run.
        self.mock_config.run()

        # Assert.
        mock_get_arg_parser.assert_called_once_with()
        mock_set_option.assert_called_once_with("section_name", "option_name", "option_value")

    @patch.object(argparse.ArgumentParser, "parse_args")
    def test_run_with_incorrect_args(self, mock_parse_args: MagicMock) -> None:
        """Test the run method when both positional and optional arguments are passed.

        GIVEN a ConfigCLI object,
            AND the _get_arg_parser method of this object returns an argparse.ArgumentParser object
            AND calling the parse_args method on this returns an argparse.Namespace object with the name and
                edit arguments being not the default.
        WHEN calling the run method on the ConfigCLI object
        THEN SystemExit exception should be raised with errorcode 2 by the error method of the parser object that was
                called with the correct message.
        """
        # Setup environment.
        self.mock_config._config_file = Path("/foo/bar")
        args = argparse.Namespace(
            name="section_name.option_name",
            value=None,
            unset_name=None,
            list=False,
            edit=True,
            unset_all=False,
            list_valid_options=False,
        )
        mock_parse_args.return_value = args

        # Run and assert.
        with self.assertRaises(SystemExit) as cm, patch("sys.stderr", new_callable=StringIO):
            self.mock_config.run()
        self.assertEqual(cm.exception.code, 2)

    @patch.object(ConfigCLI, "_unset_option")
    @patch.object(ConfigCLI, "_get_arg_parser")
    def test_run_with_unset_name(self, mock_get_arg_parser: MagicMock, mock_unset_option: MagicMock) -> None:
        """Test the run method when unset_name is passed.

        GIVEN a ConfigCLI object,
            AND the _get_arg_parser method of this object returns an argparse.ArgumentParser object
            AND calling the parse_args method on this returns an argparse.Namespace object with the unset_name arguments
                being not the default.
        WHEN calling the run method on the ConfigCLI object
        THEN the _unset_option method of this object should be called once with the correct args.
        """
        # Setup environment.
        mock_parser = create_autospec(argparse.ArgumentParser)
        args = argparse.Namespace(
            name=None,
            value=None,
            unset_name="section_name.option_name",
            list=False,
            edit=False,
            unset_all=False,
            list_valid_options=False,
        )
        mock_parser.parse_args.return_value = args
        mock_get_arg_parser.return_value = mock_parser

        # Run.
        self.mock_config.run()

        # Assert.
        mock_get_arg_parser.assert_called_once_with()
        mock_unset_option.assert_called_once_with("section_name", "option_name")

    @patch.object(ConfigCLI, "_unset_all")
    @patch.object(ConfigCLI, "_get_arg_parser")
    def test_run_with_unset_all(self, mock_get_arg_parser: MagicMock, mock_unset_all: MagicMock) -> None:
        """Test the run method when unset_all=True is passed.

        GIVEN a ConfigCLI object,
            AND the _get_arg_parser method of this object returns an argparse.ArgumentParser object
            AND calling the parse_args method on this returns an argparse.Namespace object with True unset_all argument
        WHEN calling the run method on the ConfigCLI object
        THEN the _unset_all method of this object should be called.
        """
        # Setup environment.
        mock_parser = create_autospec(argparse.ArgumentParser)
        args = argparse.Namespace(
            name=None, value=None, unset_name=None, list=False, edit=False, unset_all=True, list_valid_options=False
        )
        mock_parser.parse_args.return_value = args
        mock_get_arg_parser.return_value = mock_parser

        # Run.
        self.mock_config.run()

        # Assert.
        mock_get_arg_parser.assert_called_once_with()
        mock_unset_all.assert_called_once_with()

    @patch.object(ConfigCLI, "_list")
    @patch.object(ConfigCLI, "_get_arg_parser")
    def test_run_with_list(self, mock_get_arg_parser: MagicMock, mock_list: MagicMock) -> None:
        """Test the run method when list=True is passed.

        GIVEN a ConfigCLI object,
            AND the _get_arg_parser method of this object returns an argparse.ArgumentParser object
            AND calling the parse_args method on this returns an argparse.Namespace object with True list argument
        WHEN calling the run method on the ConfigCLI object
        THEN the _list method of this object should be called.
        """
        # Setup environment.
        mock_parser = create_autospec(argparse.ArgumentParser)
        args = argparse.Namespace(
            name=None, value=None, unset_name=None, list=True, edit=False, unset_all=False, list_valid_options=False
        )
        mock_parser.parse_args.return_value = args
        mock_get_arg_parser.return_value = mock_parser

        # Run.
        self.mock_config.run()

        # Assert.
        mock_get_arg_parser.assert_called_once_with()
        mock_list.assert_called_once_with()

    @patch.object(ConfigCLI, "_print_valid_config")
    @patch.object(ConfigCLI, "_get_arg_parser")
    def test_run_with_list_valid_options(
        self, mock_get_arg_parser: MagicMock, mock_print_valid_config: MagicMock
    ) -> None:
        """Test the run method when list_valid_options=True is passed.

        GIVEN a ConfigCLI object,
            AND the _get_arg_parser method of this object returns an argparse.ArgumentParser object
            AND calling parse_args method on this returns an argparse.Namespace with True list_valid_options argument
        WHEN calling the run method on the ConfigCLI object
        THEN the _print_valid_config method of this object should be called.
        """
        # Setup environment.
        mock_parser = create_autospec(argparse.ArgumentParser)
        args = argparse.Namespace(
            name=None, value=None, unset_name=None, list=False, edit=False, unset_all=False, list_valid_options=True
        )
        mock_parser.parse_args.return_value = args
        mock_get_arg_parser.return_value = mock_parser

        # Run.
        self.mock_config.run()

        # Assert.
        mock_get_arg_parser.assert_called_once_with()
        mock_print_valid_config.assert_called_once_with()

    @patch.object(ConfigCLI, "_edit")
    @patch.object(ConfigCLI, "_get_arg_parser")
    def test_run_with_edit(self, mock_get_arg_parser: MagicMock, mock_edit: MagicMock) -> None:
        """Test the run method when edit=True is passed.

        GIVEN a ConfigCLI object,
            AND the _get_arg_parser method of this object returns an argparse.Argumentparser object
            AND calling the parse_args method on this returns an argparse.Namespace object with the edit argument being
                True.
        WHEN calling the run method on the ConfigCLI object
        THEN the _edit method of this object should be called.
        """
        # Setup environment.
        self.mock_config._schema = True
        mock_parser = create_autospec(argparse.ArgumentParser)
        args = argparse.Namespace(
            name=None, value=None, unset_name=None, list=False, edit=True, unset_all=False, list_valid_options=False
        )
        mock_parser.parse_args.return_value = args
        mock_get_arg_parser.return_value = mock_parser

        # Run.
        self.mock_config.run()

        # Assert.
        mock_get_arg_parser.assert_called_once_with()
        mock_edit.assert_called_once_with()

    @patch.object(ConfigCLI, "_get_arg_parser")
    def test_run_with_no_args(self, mock_get_arg_parser: MagicMock) -> None:
        """Test the run method when no arg is passed.

        GIVEN a ConfigCLI object,
            AND the _get_arg_parser method of this object returns an argparse.Argumentparser object
            AND calling the parse_args method on this returns an argparse.Namespace object with all arguments being
                default.
        WHEN calling the run method on the ConfigCLI object
        THEN the print_help method of the parser object should be called.
        """
        # Setup environment.
        self.mock_config._schema = None
        mock_parser = create_autospec(argparse.ArgumentParser)
        args = argparse.Namespace(
            name=None, value=None, unset_name=None, list=False, edit=False, unset_all=False, list_valid_options=False
        )
        mock_parser.parse_args.return_value = args
        mock_get_arg_parser.return_value = mock_parser

        # Run.
        self.mock_config.run()

        # Assert.
        mock_get_arg_parser.assert_called_once_with()
        mock_parser.print_help.assert_called_once_with()

    @patch.object(ConfigCLI, "save")
    @patch("confinator.cli.ValidConfig.set")
    @patch("confinator.cli.ValidConfig.add_section")
    @patch("confinator.cli.ValidConfig.has_section", return_value=True)
    def test_set_option_with_existing_section(
        self, mock_has_section: MagicMock, mock_add_section: MagicMock, mock_set: MagicMock, mock_save: MagicMock
    ) -> None:
        """Test the _set_option method when the passed section already exists.

        GIVEN a ConfigCLI object,
            AND a section name, an option name and a value
            AND the has_section method of the ConfigParser class returns True
        WHEN calling the _set_option method of the ConfigCLI object with the section, option and value.
        THEN the has_section method of the ConfigParser class should be called once with the section,
            AND the set method of the ConfigParser class should be called once with the section, option and value,
            AND the save of the ConfigCLI object should be called once.
        """
        # Setup environment.
        section = "section_name"
        option = "option_name"
        value = "new_value"

        # Run.
        self.mock_config._set_option(section, option, value)

        # Assert.
        mock_has_section.assert_called_once_with(section)
        mock_add_section.assert_not_called()
        mock_set.assert_called_once_with(section, option, value)
        mock_save.assert_called_once_with()

    @patch.object(ConfigCLI, "save")
    @patch("confinator.cli.ValidConfig.set")
    @patch("confinator.cli.ValidConfig.add_section")
    @patch("confinator.cli.ValidConfig.has_section", return_value=False)
    def test_set_option_with_non_existing_section(
        self, mock_has_section: MagicMock, mock_add_section: MagicMock, mock_set: MagicMock, mock_save: MagicMock
    ) -> None:
        """Test the _set_option method when the passed section doesn't exists.

        GIVEN a ConfigCLI object,
            AND a section name, an option name and a value
            AND the has_section method of the ConfigParser class returns False
        WHEN calling the _set_option method of the ConfigCLI object with the section, option and value.
        THEN the has_section method of the ConfigParser class should be called once with the section,
            AND the add_section method of the ConfigParser class should be called once with the section,
            AND the set method of the ConfigParser class should be called once with the section, option and value,
            AND the save of the ConfigCLI object should be called once.
        """
        # Setup environment.
        section = "section_name"
        option = "option_name"
        value = "new_value"

        # Run.
        self.mock_config._set_option(section, option, value)

        # Assert.
        mock_has_section.assert_called_once_with(section)
        mock_add_section.assert_called_once_with(section)
        mock_set.assert_called_once_with(section, option, value)
        mock_save.assert_called_once_with()

    @patch("sys.stdout", new_callable=StringIO)
    @patch("confinator.cli.ValidConfig.get", return_value="option_value")
    def test_get_option_with_existing_option(self, mock_get: MagicMock, mock_stdout: MagicMock) -> None:
        """Test _get_option method with existing option.

        GIVEN a ConfigCLI object,
            AND a section and an option name,
            AND the get method of the ConfigParser class returns a given value
        WHEN calling the _get_option method of the ConfigCLI object with the section and option names,
        THEN the get method of the ConfigParser class should be called once with them
            AND the returned value should be printed on the stdout with a newline char at the end.
        """
        # Setup environment.
        section = "section_name"
        option = "option_name"

        # Run.
        self.mock_config._get_option(section, option)

        # Assert.
        mock_get.assert_called_once_with(section, option)
        self.assertEqual(mock_stdout.getvalue(), "option_value\n")

    @patch("sys.stdout", new_callable=StringIO)
    @patch("confinator.cli.ValidConfig.get")
    def test_get_option_with_non_existing_option(self, mock_get: MagicMock, mock_stdout: MagicMock) -> None:
        """Test _get_option method with non existing option.

        GIVEN a ConfigCLI object,
            AND a section and an option name,
            AND the get method of the ConfigParser class returns a given value
        WHEN calling the _get_option method of the ConfigCLI object with the section and option names,
        THEN the get method of the ConfigParser class should be called once with them
            AND the returned value should be printed on the stdout with a newline char at the end.
        """
        # Setup environment.
        section = "section_name"
        option = "option_name"
        mock_get.side_effect = [NoSectionError(section), NoOptionError(section, option)]

        # Run and assert 1.
        with self.assertRaises(SystemExit) as cm, patch("sys.stderr", new_callable=StringIO) as mock_stderr:
            self.mock_config._get_option(section, option)
        self.assertEqual(cm.exception.code, 1)
        mock_get.assert_called_once_with(section, option)
        self.assertEqual(mock_stderr.getvalue(), "No section: 'section_name'\n")

        mock_get.reset_mock()

        # Run and assert 2.
        with self.assertRaises(SystemExit) as cm, patch("sys.stderr", new_callable=StringIO) as mock_stderr:
            self.mock_config._get_option(section, option)
        self.assertEqual(cm.exception.code, 1)
        mock_get.assert_called_once_with(section, option)
        self.assertEqual(mock_stderr.getvalue(), "No option 'section_name' in section: 'option_name'\n")

        self.assertEqual(mock_stdout.getvalue(), "")

    @patch.object(ConfigCLI, "save")
    @patch("confinator.cli.ValidConfig.remove_section")
    @patch("confinator.cli.ValidConfig.options", side_effect=[["another_option"], []])
    @patch("confinator.cli.ValidConfig.remove_option", return_value=True)
    def test_unset_option_with_existing_option(
        self,
        mock_remove_option: MagicMock,
        mock_options: MagicMock,
        mock_remove_section: MagicMock,
        mock_save: MagicMock,
    ) -> None:
        """Test the _unset_option method with existing method when the option to be removed is not the last option in
        the given section.

        GIVEN a ConfigCLI object,
            AND the remove_option method of its parent class returns True,
            AND the options method of its parent returns a list with one option_name first and an empty list second.
            AND a section and option names.
        WHEN calling the _unset_option method on the ConfigCLI object with this section and option two times,
        THEN the remove_options method should be called with this section and option name both time,
            AND then the options method of the parent class should be called with the section name to see if there is
                any remaining option in the given section (and there is one) also both time,
            AND the remove_section method should be called only for the second time with the section name,
            AND finally the save method of the ConfigCLI object should be called both time.
        """
        # Setup environment.
        section = "section_name"
        option = "option_name"

        mock_parent = Mock()
        mock_parent.attach_mock(mock_remove_option, "mock_remove_option")
        mock_parent.attach_mock(mock_options, "mock_options")
        mock_parent.attach_mock(mock_remove_section, "mock_remove_section")
        mock_parent.attach_mock(mock_save, "mock_save")

        # Run 1.
        self.mock_config._unset_option(section, option)
        # Assert 1.
        mock_parent.assert_has_calls(
            [call.mock_remove_option(section, option), call.mock_options(section), call.mock_save()]
        )

        mock_parent.reset_mock()

        # Run 2.
        self.mock_config._unset_option(section, option)
        # Assert 2.
        mock_parent.assert_has_calls(
            [
                call.mock_remove_option(section, option),
                call.mock_options(section),
                call.mock_remove_section(section),
                call.mock_save(),
            ]
        )

    @patch.object(ConfigCLI, "save")
    @patch("confinator.cli.ValidConfig.remove_option", return_value=False)
    def test_unset_option_with_not_existing_option(self, mock_remove_option: MagicMock, mock_save: MagicMock) -> None:
        """Test the _unset_option method when the option doesn't exist in the section.

        GIVEN a ConfigCLI object,
            AND a section and option names,
            AND the remove_option method returns False.
        WHEN calling the _unset_option method on the ConfigCLI object with this section and option,
        THEN first the remove_options method should be called with this section and option name,
            AND no other methods should be called then especially not the save method.
        """
        # Setup environment.
        section = "section_name"
        option = "option_name"

        # Run.
        self.mock_config._unset_option(section, option)

        # Assert.
        mock_remove_option.assert_called_once_with(section, option)
        mock_save.assert_not_called()

    @patch("confinator.cli.ValidConfig.remove_option", side_effect=NoSectionError("section_name"))
    def test_unset_option_with_not_existing_section(self, mock_remove_option: MagicMock) -> None:
        """Test the _unset_option method when the section doesn't exist.

        GIVEN a ConfigCLI object,
            AND a section and option names,
            AND the remove_option method raises NoSectionError.
        WHEN calling the _unset_option method on the ConfigCLI object with this section and option,
        THEN first the remove_options method should be called with this section and option name,
            AND it should raise SystemExit exception and thus terminate the code with error code 1 and appropriate
                message printed to the stderr.
        """
        # Setup environment.
        section = "section_name"
        option = "option_name"

        # Run.
        with self.assertRaises(SystemExit) as cm, patch("sys.stderr", new_callable=StringIO) as mock_stderr:
            self.mock_config._unset_option(section, option)
        self.assertEqual(cm.exception.code, 1)
        self.assertEqual(mock_stderr.getvalue(), "No section: 'section_name'\n")

        # Assert.
        mock_remove_option.assert_called_once_with(section, option)

    @patch.object(ConfigCLI, "save")
    @patch("confinator.cli.ValidConfig.remove_section")
    @patch("confinator.cli.ValidConfig.sections", return_value=["first_section", "second_section"])
    def test_unset_all(self, mock_sections: MagicMock, mock_remove_section: MagicMock, mock_save: MagicMock) -> None:
        """Test the _unset_all method.

        GIVEN a ConfigCLI object,
            AND its sections method of its parent returns 2 section names as defined.
        WHEN calling the _unset_all method on the ConfigCLI object,
        THEN the sections method should be called once first,
            AND then the remove_section method of the parent class should be called with each section name returned from
                the sections call,
            AND finally the save method of the ConfigCLI object should be called once.
        """
        # Setup environment.
        # Attach mocks to a parent mock in order to be able to check the order of the method calls.
        mock_parent = Mock()
        mock_parent.attach_mock(mock_sections, "mock_sections")
        mock_parent.attach_mock(mock_remove_section, "mock_remove_section")
        mock_parent.attach_mock(mock_save, "mock_save")

        # Run.
        self.mock_config._unset_all()

        # Assert.
        mock_parent.assert_has_calls(
            [
                call.mock_sections(),
                call.mock_remove_section("first_section"),
                call.mock_remove_section("second_section"),
                call.mock_save(),
            ]
        )

    @patch("confinator.cli.ValidConfig.get", side_effect=["first_value", "second_value", "third_value", "fourth_value"])
    @patch(
        "confinator.cli.ValidConfig.options",
        side_effect=[["first_option", "second_option"], ["third_option", "fourth_option"]],
    )
    @patch("confinator.cli.ValidConfig.sections", return_value=["first_section", "second_section"])
    def test_list(self, mock_sections: MagicMock, mock_options: MagicMock, mock_get: MagicMock) -> None:
        """Test the _list method.

        GIVEN a ConfigCLI object,
            AND its sections method returns 2 sections
            AND its options method returns 2 options for each section.
        WHEN calling the _list method on this object.
        THEN it should print the options to the stdout in the format of "section_name.option_name=option_value" for each
                option in a separate row.
        """
        # Run.
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            self.mock_config._list()

        # Assert.
        mock_sections.assert_called_once()
        self.assertEqual(mock_options.call_args_list, [call("first_section"), call("second_section")])
        self.assertEqual(
            mock_get.call_args_list,
            [
                call("first_section", "first_option"),
                call("first_section", "second_option"),
                call("second_section", "third_option"),
                call("second_section", "fourth_option"),
            ],
        )
        self.assertEqual(
            mock_stdout.getvalue(),
            "first_section.first_option=first_value\n"
            "first_section.second_option=second_value\n"
            "second_section.third_option=third_value\n"
            "second_section.fourth_option=fourth_value\n",
        )

    @patch("builtins.print")
    def test_print_valid_config(self, mock_print: MagicMock) -> None:
        """Test the _print_valid_config method.

        GIVEN a ConfigCLI object,
            AND its _schema_file attribute is a pathlib.Path object.
        WHEN calling the _print_valid_config on the ConfigCLI object,
        THEN it should open this file and print its content to the stdout.
        """
        # Setup environment.
        mock_path = create_autospec(Path)
        self.mock_config._schema_file = mock_path

        # Run.
        self.mock_config._print_valid_config()

        # Assert.
        mock_print.assert_called_once_with(mock_path.open.return_value.__enter__.return_value.read.return_value)

    @patch("confinator.cli.subprocess.run")
    def test_edit(self, mock_run: MagicMock) -> None:
        """Test the _edit method.

        GIVEN a ConfigCLI object,
            AND its _config_file attribute is a pathlib.Path object.
        WHEN calling the _edit method of the ConfigCLI object with different environment variables.
        THEN it should call the run method of the subprocess module with the first provided and not empty editor in the
                order of VISUAL > EDITOR > vim, plus the _config_file attribute appended to the command.
        """
        # Setup environment.
        self.mock_config._config_file = create_autospec(Path)
        envs = [{"VISUAL": "code", "EDITOR": "atom"}, {"VISUAL": "code"}, {"VISUAL": ""}, {"EDITOR": "atom"}, {}]
        editors = ["code", "code", "vim", "atom", "vim"]

        # Run and assert.
        for env, editor in zip(envs, editors):
            with self.subTest(env=env), patch.dict(os.environ, env):
                self.mock_config._edit()
                mock_run.assert_called_once_with([editor, self.mock_config._config_file])
            mock_run.reset_mock()


def mock_read(self, f):
    self.read_file(f)
    return True


class TestCLIConfigFunctionality(unittest.TestCase):
    """Higher level tests for the ConfigCLI class."""

    @patch("confinator.cli.Path", lambda x: x)
    @patch("confinator.validation.ConfigParser.read", mock_read)
    def setUp(self) -> None:
        """Entry point for all tests."""
        self.mock_config_file = StringIO(
            "[section_1]\n"
            "option_1 = value_1\n"
            "option_2 = value_2\n"
            "\n"
            "[section_2]\n"
            "option_3 = value_3\n"
            "\n"
        )
        self.mock_schema_file = StringIO(
            "[^section_1$]\n"
            "^option_1$ = ^value_\d$\n"
            "^option_2$ = ^value_2$\n"
            "^new_option$ = ^new_value$\n"
            "\n"
            "[^section_2$]\n"
            "^option_3$ = ^value_3$\n"
            "\n"
        )
        self.mock_config_file.parent = Mock()
        self.mock_config_file_2 = StringIO()
        self.mock_config_file_2.close = Mock()
        self.mock_config_file.open = Mock(return_value=self.mock_config_file_2)
        self.config = ConfigCLI(self.mock_config_file, self.mock_schema_file)

    @patch.object(sys, "argv", ["config", "section_1.new_option", "new_value"])
    def test_set_option_adding_new_option(self) -> None:
        """Test the set value functionality when it tries to add a new option.

        GIVEN a ConfigCLI object.
            AND the script was called with two positional arguments (meaning that an option should be set)
        WHEN calling the run method on this ConfigCLI object.
        THEN the new option should be added and the config should be dumped to the file.
        """
        # Run.
        self.config.run()

        # Assert.
        self.assertEqual(
            self.mock_config_file_2.getvalue(),
            "[section_1]\n"
            "option_1 = value_1\n"
            "option_2 = value_2\n"
            "new_option = new_value\n"
            "\n"
            "[section_2]\n"
            "option_3 = value_3\n"
            "\n",
        )

    @patch.object(sys, "argv", ["config", "section_1.option_1", "value_0"])
    def test_set_option_setting_existing_option(self) -> None:
        """Test the set value functionality when it tries to set an existing option.

        GIVEN a ConfigCLI object.
            AND the script was called with two positional arguments (meaning that an option should be set)
        WHEN calling the run method on this ConfigCLI object.
        THEN the existing option should get a new value and the config should be dumped to the file.
        """
        # Run.
        self.config.run()

        # Assert.
        self.assertEqual(
            self.mock_config_file_2.getvalue(),
            "[section_1]\n"
            "option_1 = value_0\n"
            "option_2 = value_2\n"
            "\n"
            "[section_2]\n"
            "option_3 = value_3\n"
            "\n",
        )

    @patch.object(sys, "argv", ["config", "--unset", "section_1.option_2"])
    def test_unset_option(self) -> None:
        """Test the unset option functionality.

        GIVEN a ConfigCLI object.
            AND the script was called with --unset NAME arguments
        WHEN calling the run method on this ConfigCLI object.
        THEN the existing option should get removed and the config should be dumped to the file.
        """
        # Run.
        self.config.run()

        # Assert.
        self.assertEqual(
            self.mock_config_file_2.getvalue(),
            "[section_1]\n" "option_1 = value_1\n" "\n" "[section_2]\n" "option_3 = value_3\n" "\n",
        )

    @patch.object(sys, "argv", ["config", "--unset-all"])
    def test_unset_all(self) -> None:
        """Test the unset all option functionality.

        GIVEN a ConfigCLI object.
            AND the script was called with --unset-all argument
        WHEN calling the run method on this ConfigCLI object.
        THEN all the existing options should get removed and the config should be dumped to the file.
        """
        # Run.
        self.config.run()

        # Assert.
        self.assertEqual(self.mock_config_file_2.getvalue(), "")

    @patch.object(sys, "argv", ["config", "-l"])
    def test_list(self) -> None:
        """Test the list functionality.

        GIVEN a ConfigCLI object.
            AND the script was called with -l argument
        WHEN calling the run method on this ConfigCLI object.
        THEN it should print all available options to the stdout.
        """
        # Run.
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            self.config.run()

        # Assert.
        self.assertEqual(
            mock_stdout.getvalue(),
            "section_1.option_1=value_1\n" "section_1.option_2=value_2\n" "section_2.option_3=value_3\n",
        )


if __name__ == "__main__":
    unittest.main()
