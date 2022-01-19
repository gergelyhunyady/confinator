# Confinator

`confinator` is a small python package aiming to bring for the configuration management of your python applications:
- convenience and style from user perspective,
- clean structure and ease of implementation from the developers point of view.  

It actually provides:
- a `git config` like command line interface for any of your application using INI style config file(s),
- dynamic validation of the config sections, options and values - using regular expressions,
- example application using a practical layout when using `confinator`.

__Behold the power of `confinator`:__ 

TODO

## Installation
Requires python 3.8+

TODO

## Getting Started

- [ Tutorial ](#tutorial)
- [ Explanation ](#explanation)
- [ API Reference ](#api_reference)
  - [ ConfigCLI ](#configcli)
  - [ ValidConfig ](#validconfig)
  - [ validate_config ](#validate_config)
- [ How-To ](#how_to)
  - [Regular expression](#regexp)

<a name="tutorial"></a>
### Tutorial
Check the example application in the [example_app](./example_app) directory.

TODO

<a name="explanation"></a>
### Explanation
`confinator` builds on top of the python standard library exclusively.
No other 3rd party _requirements / imports_ are used.

The functionality heavily _depends / builds_ on [configparser](https://docs.python.org/3/library/configparser.html).

<a name="api_reference"></a>
### API Reference

<a name="configcli"></a>
#### cli.ConfigCLI

```python
class ConfigCLI(
    config_file: Union[Path, str],
    schema_file: Union[Path, str],
    **kwargs,
)
```
This class helps creating scripts that can get and set options in a given INI style config files via the command line
providing `git config` like syntax for the users.

`config_file` is the path to the INI style configuration file that we want to connect to. If the file doesn't exist,
an empty configuration is assumed, and the config file will be created upon the first action that adds something to the
config.

`schema_file` is a path to a special INI config file that will be used to validate existing and newly added options and
values. For more details on the file format check the same argument of the [ValidConfig](#ValidConfig) class. 

The class inherits from the `ValidConfig` class.
Further keyword arguments can be passed to this parent class.

__Usage example:__

Create the script named e.g. `app_config`:
```python
#!/usr/bin/env python3

import sys
from confinator.cli import ConfigCLI

cli = ConfigCLI(config_file=<USER_CONFIG_PATH>, schema_file=<SCHEMA_CONFIG_PATH>)
cli.run()
```
Get help for available actions:
```
$ /path/to/script/app_config -h 
usage: app_config [-h | name | name value | -l | -e | --unset NAME | --unset-all | --list-valid-options]

Get or set options in the config file located at /path/to/config/file

positional arguments:
  name                  Name of the config parameter to get or set in
                        "section.option" format.
  value                 Value of the config parameter to set.

optional arguments:
  -h, --help            show this help message and exit

Actions:
  -l, --list            List all variables set in the config file.
  -e, --edit            Opens the config file with the default editor.
  --unset NAME          Remove a variable by name from the config file.
  --unset-all           Remove all variables from the config file.
  --list-valid-options  List the valid section, option and value formats.
```
Most used commands:
```
cli_config foo.bar                  # Get the value of the bar option from section named foo.
cli_config foo.bar baz              # Set the value of the bar option in section named foo to baz.
cli_config --unset foo.bar          # Remove the bar option from section named foo.
```

<a name="validconfig"></a>
#### validation.ValidConfig

```python
class ValidConfig(
    config_file: Union[Union[Path, str], List[Union[Path, str]]],
    schema_file: Union[Path, str],
    use_case_sensitive_option_names: bool = False,
    **kwargs,
)
```
Read INI style config_file(s) into a [`configparser.Configparser`](https://docs.python.org/3/library/configparser.html#configparser.ConfigParser)
representation and validate the section and option names, and also their value against a schema.

`config_file` is the path of the INI config file that will be loaded, or a list of hierarchical config files.
For more detail read [THIS](https://docs.python.org/3/library/configparser.html#configparser.ConfigParser.read).

`schema_file` is a path to a special INI config file that will be used to validate the config file when loading.
This special config file should contain all the possible sections, options and their values as regular expressions.
Example format:
```
[^section_foo_.*$]
^option_a$ = ^.+$
^option_b$ = ^\d{8}$

[^section_bar$]
^.*_some_suffix$ = ^(1|yes|true|on|0|no|false|off)$ 
^option_c$ = ^\w+$
```
`use_case_sensitive_option_names` will disable the default behavior of converting each option name
to lowercase when reading the config file.

Further `**kwargs` will be passed to the underlying `configparser.Configparser` constructor.

`ValidConfig` subclasses [`configparser.Configparser`](https://docs.python.org/3/library/configparser.html#configparser.ConfigParser)
thus you can use all its methods to manipulate the config. NOTE that the special "DEFAULT" section is not supported.

##### save()
Validate and then dump the content of the in memory config to the `config_file`.

<a name="validate_config"></a>
#### validation.validate_config
```python
validate_config(config: ConfigParser, schema: ConfigParser) -> None
```
Validate the `config` against the `schema` using regular expressions.
Refer to the description of the [ ValidConfig ](#ValidConfig) class for more detail on the schema.

Raises `InvalidSectionError`, `InvalidOptionError` or `InvalidValueError` (all subclassing `InvalidCOnfigError`)
when the validation fails. 

<a name="how_to"></a>
### How-To

<a name="regexp"></a>
#### Regular expression
A regular expression is a sequence of characters that define a search pattern, mainly for string matching.

Start with a quick intro [HERE](https://www.geeksforgeeks.org/write-regular-expressions/).

The best way of learning regex is via using it.
[Regex101](https://regex101.com/) is a brilliant tool that will support you.