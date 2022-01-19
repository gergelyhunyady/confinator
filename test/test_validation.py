#!/usr/bin/env python3
"""Test the validation module."""

import unittest
from configparser import ConfigParser
from pathlib import Path
from unittest.mock import create_autospec, patch, MagicMock, Mock

from confinator.validation import (
    InvalidOptionError,
    InvalidSectionError,
    InvalidValueError,
    InvalidConfigError,
    ValidConfig,
    _validate_option,
    _validate_section,
    _validate_value,
    validate_config,
)


class TestValidateConfig(unittest.TestCase):
    """Test the config validation functions."""

    def test_validate_section(self) -> None:
        """Test the _validate_section function.

        GIVEN a section name,
            AND a list of valid section patterns.
        WHEN calling the _validate_section function with them,
        THEN it should raise InvalidSectionError if the section name is not matching any of the patterns
            in the valid list as a python regular expression or it is DEFAULT.
        """
        # Setup environment.
        section_sequence = ["test_section", "section_bar", "DEFAULT"]
        valid_sections = ["section_foo", "^sect.*_bar$", "DEFAULT"]

        for section in section_sequence:
            with self.subTest(section=section):
                # Run and assert.
                if section == "section_bar":
                    result = _validate_section(section, valid_sections)
                    self.assertEqual(result, "^sect.*_bar$")
                else:
                    with self.assertRaises(InvalidSectionError):
                        _validate_section(section, valid_sections)

    def test_validate_option(self) -> None:
        """Test the _validate_section function.

        GIVEN a section and option names,
            AND a list of valid option patterns.
        WHEN calling the _validate_option function with them,
        THEN it should raise InvalidOptionError if the option name is not matching any of the patterns
                in the valid list as a python regular expression.
        """
        # Setup environment.
        section = "test_section"
        option_sequence = ["test_option", "option_bar"]
        valid_options = ["option_foo", "^opt.*_bar$"]

        for option in option_sequence:
            with self.subTest(option=option):
                # Run and assert.
                if option == "option_bar":
                    result = _validate_option(section, option, valid_options)
                    self.assertEqual(result, "^opt.*_bar$")
                else:
                    with self.assertRaises(InvalidOptionError):
                        _validate_option(section, option, valid_options)

    def test_validate_value(self) -> None:
        """Test the _validate_value function.

        GIVEN a section and option names and a value for it,
            AND a valid value pattern.
        WHEN calling the _validate_value function with them,
        THEN it should raise InvalidValueError if the value is not matching the pattern.
        """
        # Setup environment.
        section = "test_section"
        option = "test_option"
        value_sequence = ["test_value", "12308"]
        valid_value = r"^\d{5}$"

        for value in value_sequence:
            with self.subTest(value=value):
                # Run and assert.
                if value == "12308":
                    _validate_value(section, option, value, valid_value)
                else:
                    with self.assertRaises(InvalidValueError):
                        _validate_value(section, option, value, valid_value)

    def test_validate_config(self) -> None:
        """Test the validate_config function.

        GIVEN two ConfigParser objects,
        WHEN calling the validate_config function with them.
        THEN the first should be validated against the second. Each section, option and value in the first config should
                match its relevant regex pattern in the second to pass.
            AND it should raise InvalidConfigError if the config is not valid.
        """
        # Setup environment.
        schema = ConfigParser()
        schema["^section_foo$"] = {"^option_a$": r"^\d{5}$", "^option_b$": r"^(de|us)$", "^option_c$": r"^\w+$"}
        schema["^section_bar$"] = {"^option_a$": r"^(1|yes|true|on|0|no|false|off)$", "^option_d$": r"^(de|us)$"}

        config_0 = ConfigParser()

        config_1 = ConfigParser()
        config_1["section_foo"] = {"option_a": "12345", "option_b": "us"}
        config_1["section_bar"] = {"option_a": "true"}

        config_2 = ConfigParser()
        config_2["section_foo"] = {"option_a": "1a2345", "option_b": "us"}
        config_2["section_bar"] = {"option_a": "true"}

        config_3 = ConfigParser()
        config_3["section_foo"] = {"option_a": "122345", "option_b": "us", "option_baz": "58"}
        config_3["section_bar"] = {"option_a": "true"}

        config_4 = ConfigParser()
        config_4["section_foo"] = {"option_a": "12345", "option_b": "us"}
        config_4["section_bar"] = {"option_a": "true"}
        config_4["section_baz"] = {"option_a": "true"}

        config_sequence = [config_0, config_1, config_2, config_3, config_4]
        ok_sequence = [True, True, False, False, False]

        for config, ok in zip(config_sequence, ok_sequence):
            with self.subTest():
                # Run and assert.
                if ok:
                    validate_config(config, schema)
                else:
                    with self.assertRaises(InvalidConfigError):
                        validate_config(config, schema)


class TestValidConfig(unittest.TestCase):
    """Test the ValidConfig class."""

    @patch.object(ValidConfig, "_validate")
    @patch.object(ValidConfig, "_get_schema")
    @patch("confinator.validation.ConfigParser.read")
    @patch("confinator.validation.ConfigParser.__init__")
    def test_init(
        self, mock_parent_init: MagicMock, mock_read: MagicMock, mock_get_schema: MagicMock, mock_validate: MagicMock
    ) -> None:
        """Test the initialization of the class.

        WHEN creating a ValidConfig object,
        THEN it should call the parent __init__ with correct args,
            AND it should call the read method of the parent with the config_file argument,
            AND it should call the _get_schema method of the ValidConfig class with the schema_file argument,
            AND then it should call the _validate method.
            AND the _schema attribute of the created object should be the returned object from the _get_schema call.
        """
        # Setup environment.
        argument_sequence = [
            {"config_file": create_autospec(Path), "schema_file": create_autospec(Path)},
            {
                "config_file": create_autospec(Path),
                "schema_file": create_autospec(Path),
                "use_case_sensitive_option_names": True,
                "first": 5,
                "second": Mock(),
            },
        ]

        for kwargs in argument_sequence:
            with self.subTest(**kwargs):
                # Run.
                valid_config = ValidConfig(**kwargs)

                # Assert.
                mock_parent_init.assert_called_once_with(
                    **{
                        key: value
                        for key, value in kwargs.items()
                        if key not in ["config_file", "schema_file", "use_case_sensitive_option_names"]
                    }
                )
                if kwargs.get("use_case_sensitive_option_names") is True:
                    self.assertEqual(valid_config.optionxform("CAPS"), "CAPS")
                else:
                    self.assertEqual(valid_config.optionxform("CAPS"), "caps")
                mock_read.assert_called_once_with(kwargs["config_file"])
                mock_get_schema.assert_called_once_with(kwargs.get("schema_file"))
                self.assertEqual(valid_config._schema, mock_get_schema.return_value)
                mock_validate.assert_called_once_with()

            # Reset mocks.
            mock_parent_init.reset_mock()
            mock_read.reset_mock()
            mock_get_schema.reset_mock()
            mock_validate.reset_mock()

    @patch.object(ValidConfig, "__init__", lambda *_: None)
    @patch("confinator.validation.ConfigParser")
    def test_get_schema(self, mock_config_parser: MagicMock) -> None:
        """Test the _get_schema method.

        GIVEN a ValidConfig object
        WHEN calling the _get_schema method on it with a path.
        THEN it should return a ConfigParser object loaded from the passed file.
        """
        # Setup environment.
        valid_config = ValidConfig()
        schema_file = Path("/test/path")

        # Run.
        schema = valid_config._get_schema(schema_file)

        # Assert.
        mock_config_parser.assert_called_once_with(inline_comment_prefixes=["#"])
        mock_config_parser.return_value.read.assert_called_once_with(schema_file)
        self.assertEqual(schema, mock_config_parser.return_value)

    @patch.object(ValidConfig, "__init__", lambda *_: None)
    @patch("confinator.validation.validate_config")
    def test_validate(self, mock_validate_config: MagicMock) -> None:
        """Test the _validate method.

        GIVEN a ValidConfig object
        WHEN calling the _validate method on it
        THEN is should call the validate_config function with the ValidConfig object and the _schema attribute of it.
        """
        # Setup environment.
        valid_config = ValidConfig()
        valid_config._schema = ConfigParser()

        # Run
        valid_config._validate()

        # Assert
        mock_validate_config.assert_called_once_with(valid_config, valid_config._schema)

    @patch.object(ValidConfig, "__init__", lambda *_: None)
    @patch.object(ValidConfig, "_validate")
    @patch("confinator.validation.ConfigParser.write")
    def test_save(self, mock_write: MagicMock, mock_validate: MagicMock) -> None:
        """Test the save method.

        GIVEN a ValidConfig object,
            AND its _config_file attribute is a pathlib.Path
        WHEN calling the save method on the ValidConfig object,
        THEN its _validate method should be called once,
            AND the mkdir method should be called on the parent of the _config_file attribute with correct arguments.
            AND _config_file attribute should be opened to write in a with block,
            AND the write method of the ConfigParser class should be called with the opened file object.
        """
        # Setup environment.
        valid_config = ValidConfig()
        valid_config._config_file = create_autospec(Path)

        # Run.
        valid_config.save()

        # Assert.
        mock_validate.assert_called_once_with()
        valid_config._config_file.parent.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        valid_config._config_file.open.assert_called_once_with("w")
        mock_write.assert_called_once_with(valid_config._config_file.open.return_value.__enter__.return_value)


if __name__ == "__main__":
    unittest.main()
