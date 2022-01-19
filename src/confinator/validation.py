"""Tools for INI style config file validation."""

import re
from configparser import ConfigParser
from pathlib import Path
from typing import List, Union


class InvalidConfigError(Exception):
    """Base invalid config exception. Specific config exception classes should inherit from this."""

    pass


class InvalidSectionError(InvalidConfigError):
    """Exception to raise if an invalid section name is found."""

    def __init__(self, section: str, valid_sections: List[str]) -> None:
        """Print custom error message.

        Args:
            section: name of the section
            valid_sections: list of valid section names
        """
        super().__init__(
            f'"{section}" is not a valid section. Valid sections should match one of these '
            f'as a python regular expression: {", ".join(valid_sections)}.'
        )


class InvalidOptionError(InvalidConfigError):
    """Exception to raise if a valid section has an invalid option."""

    def __init__(self, section: str, option: str, valid_options: List[str]) -> None:
        """Print custom error message.

        Args:
            section: section name
            option: option name
            valid_options: list of valid options in the given section
        """
        super().__init__(
            f'"{option}" is not a valid option for section "{section}". '
            f"Valid options in this section should match one of these as a python regular expression: "
            f'{", ".join(valid_options)}.'
        )


class InvalidValueError(InvalidConfigError):
    """Exception to raise if a valid option has an invalid value."""

    def __init__(self, section: str, option: str, value: str, valid_value: str) -> None:
        """Print custom error message.

        Args:
            section: section name
            option: option name
            value: option value
            valid_value: regexp pattern that needs to match the provided value
        """
        super().__init__(
            f'"{value}" is not a valid value for "{section}.{option}". '
            f'Should match "{valid_value}" as a python regular expression.'
        )


def _validate_section(section: str, valid_sections: List[str]) -> str:
    """Validate section name.

    Args:
        section: section name to validate
        valid_sections: list of valid section names

    Returns:
        the matching section regex string

    Raises:
        InvalidSectionError: if an invalid section name is found
    """
    for valid_section in valid_sections:
        if section != "DEFAULT" and re.compile(valid_section).match(section):
            return valid_section
    raise InvalidSectionError(section, [s for s in valid_sections if s != "DEFAULT"])


def _validate_option(section: str, option: str, valid_options: List[str]) -> str:
    """Validate option name in the given section.

    Args:
        section: section name
        option: option name to validate
        valid_options: list of valid option names as regex

    Returns:
        the matching option regex string

    Raises:
        InvalidOptionError: if a valid section has an invalid option
    """
    for valid_option in valid_options:
        if re.compile(valid_option).match(option):
            return valid_option
    raise InvalidOptionError(section, option, valid_options)


def _validate_value(section: str, option: str, value: str, valid_value: str) -> None:
    """Validate value of a given option in a given section.

    Args:
        section: section name
        option: option name
        value: value of the option
        valid_value: regex that the value should match

    Raises:
        InvalidValueError: if a valid option has an invalid value
    """
    if not re.compile(valid_value).match(value):
        raise InvalidValueError(section, option, value, valid_value)


def validate_config(config: ConfigParser, schema: ConfigParser) -> None:
    """Validate the passed config object using a validator schema.

    Args:
        config: config object to be validated
        schema: another config object with regex validator section and option names and values
    """
    for section in config.sections():
        schema_section = _validate_section(section, valid_sections=list(schema))

        for option in config.options(section):
            schema_option = _validate_option(section, option, valid_options=list(schema[schema_section]))
            _validate_value(section, option, config[section][option], valid_value=schema[schema_section][schema_option])


class ValidConfig(ConfigParser):
    """Config object loaded from file and validated."""

    def __init__(
        self,
        config_file: Union[Union[Path, str], List[Union[Path, str]]],
        schema_file: Union[Path, str],
        use_case_sensitive_option_names: bool = False,
        **kwargs,
    ) -> None:
        """Load and validate config.

        Args:
            config_file: path to the config file or list of files
            schema_file: path to a config file for validation
            use_case_sensitive_option_names: make option names case sensitive
            **kwargs: various keyword arguments that will be passed to the underlying ConfigParser initialization
        """
        super().__init__(**kwargs)
        if use_case_sensitive_option_names:
            # https://docs.python.org/3/library/configparser.html#configparser.ConfigParser.optionxform
            self.optionxform = str
        self.read(config_file)
        self._schema = self._get_schema(schema_file)
        self._validate()

    @staticmethod
    def _get_schema(schema_file: Union[Path, str]) -> ConfigParser:
        """Read schema file.

        Args:
            schema_file: path to a config file with section and option names and values using regex for validation

        Returns:
            ConfigParser: schema config loaded from the file

        Raises:
            ValueError: if the provided path doesn't point to an existing file
        """
        schema = ConfigParser(inline_comment_prefixes=["#"])
        if not schema.read(schema_file):
            raise ValueError(
                f"The provided schema_file should point to an existing config file, but there is no file "
                f"found at {schema_file}"
            )
        return schema

    def _validate(self) -> None:
        """Validate self based on the schema."""
        validate_config(self, self._schema)

    def save(self) -> None:
        """Validate and dump the config to the file."""
        self._validate()
        self._config_file.parent.mkdir(parents=True, exist_ok=True)
        with self._config_file.open("w") as f:
            self.write(f)
