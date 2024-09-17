# See the NOTICE file distributed with this work for additional information
# regarding copyright ownership.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Provide an extended version of `argparse.ArgumentParser` with additional functionality.

Examples:

    >>> from pathlib import Path
    >>> from ensembl.util.argparse import ArgumentParser
    >>> parser = ArgumentParser(description="Tool description")
    >>> parser.add_argument_src_path("--src_file", required=True, help="Path to source file")
    >>> parser.add_server_arguments(help="Server to connect to")
    >>> args = parser.parse_args()
    >>> args
    Namespace(host='myserver', port=3826, src_file=PosixPath('/path/to/src_file.txt'),
    url=URL('mysql://username@myserver:3826'), user='username')

"""

from __future__ import annotations

__all__ = [
    "ArgumentError",
    "ArgumentParser",
]

import argparse
import os
from pathlib import Path
from typing import Any, Callable

from sqlalchemy.engine import make_url, URL

from ensembl.utils import StrPath


class ArgumentError(Exception):
    """An error from creating an argument (optional or positional)."""


class ArgumentParser(argparse.ArgumentParser):
    """Extends `argparse.ArgumentParser` with additional methods and functionality.

    The default behaviour of the help text will be to display the default values on every non-required
    argument, i.e. optional arguments with `required=False`.

    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Extends the base class to include the information about default argument values by default."""
        super().__init__(*args, **kwargs)
        self.formatter_class = argparse.ArgumentDefaultsHelpFormatter
        self.__server_groups: list[str] = []

    def _validate_src_path(self, src_path: StrPath) -> Path:
        """Returns the path if exists and it is readable, raises an error through the parser otherwise.

        Args:
            src_path: File or directory path to check.

        """
        src_path = Path(src_path)
        if not src_path.exists():
            self.error(f"'{src_path}' not found")
        elif not os.access(src_path, os.R_OK):
            self.error(f"'{src_path}' not readable")
        return src_path

    def _validate_dst_path(self, dst_path: StrPath, exists_ok: bool = False) -> Path:
        """Returns the path if it is writable, raises an error through the parser otherwise.

        Args:
            dst_path: File or directory path to check.
            exists_ok: Do not raise an error during parsing if the destination path already exists.

        """
        dst_path = Path(dst_path)
        if dst_path.exists():
            if os.access(dst_path, os.W_OK):
                if exists_ok:
                    return dst_path
                self.error(f"'{dst_path}' already exists")
            else:
                self.error(f"'{dst_path}' is not writable")
        # Check if the first parent directory that exists is writable
        for parent_path in dst_path.parents:
            if parent_path.exists():
                if not os.access(parent_path, os.W_OK):
                    self.error(f"'{dst_path}' is not writable")
                break
        return dst_path

    def _validate_number(
        self,
        value: str,
        value_type: Callable[[str], int | float],
        min_value: int | float | None,
        max_value: int | float | None,
    ) -> int | float:
        """Returns the numeric value if it is of the expected type and it is within the specified range.

        Args:
            value: String representation of numeric value to check.
            value_type: Expected type of the numeric value.
            min_value: Minimum value constrain. If `None`, no minimum value constrain.
            max_value: Maximum value constrain. If `None`, no maximum value constrain.

        """
        # Check if the string representation can be converted to the expected type
        try:
            result = value_type(value)
        except (TypeError, ValueError):
            self.error(f"invalid {value_type.__name__} value: {value}")
        # Check if numeric value is within range
        if (min_value is not None) and (result < min_value):
            self.error(f"{value} is lower than minimum value ({min_value})")
        if (max_value is not None) and (result > max_value):
            self.error(f"{value} is greater than maximum value ({max_value})")
        return result

    def add_argument(self, *args: Any, **kwargs: Any) -> None:  # type: ignore[override]
        """Extends the parent function by excluding the default value in the help text when not provided.

        Only applied to required arguments without a default value, i.e. positional arguments or optional
        arguments with `required=True`.

        """
        if kwargs.get("required", False):
            kwargs.setdefault("default", argparse.SUPPRESS)
        super().add_argument(*args, **kwargs)

    def add_argument_src_path(self, *args: Any, **kwargs: Any) -> None:
        """Adds `pathlib.Path` argument, checking if it exists and it is readable at parsing time.

        If "metavar" is not defined, it is added with "PATH" as value to improve help text readability.

        """
        kwargs.setdefault("metavar", "PATH")
        kwargs["type"] = self._validate_src_path
        self.add_argument(*args, **kwargs)

    def add_argument_dst_path(self, *args: Any, exists_ok: bool = True, **kwargs: Any) -> None:
        """Adds `pathlib.Path` argument, checking if it is writable at parsing time.

        If "metavar" is not defined it is added with "PATH" as value to improve help text readability.

        Args:
            exists_ok: Do not raise an error if the destination path already exists.

        """
        kwargs.setdefault("metavar", "PATH")
        kwargs["type"] = lambda x: self._validate_dst_path(x, exists_ok)
        self.add_argument(*args, **kwargs)

    def add_argument_url(self, *args: Any, **kwargs: Any) -> None:
        """Adds `sqlalchemy.engine.URL` argument.

        If "metavar" is not defined it is added with "URI" as value to improve help text readability.

        """
        kwargs.setdefault("metavar", "URI")
        kwargs["type"] = make_url
        self.add_argument(*args, **kwargs)

    # pylint: disable=redefined-builtin
    def add_numeric_argument(
        self,
        *args: Any,
        type: Callable[[str], int | float] = float,
        min_value: int | float | None = None,
        max_value: int | float | None = None,
        **kwargs: Any,
    ) -> None:
        """Adds a numeric argument with constrains on its type and its minimum or maximum value.

        Note that the default value (if defined) is not checked unless the argument is an optional argument
        and no value is provided in the command line.

        Args:
            type: Type to convert the argument value to when parsing.
            min_value: Minimum value constrain. If `None`, no minimum value constrain.
            max_value: Maximum value constrain. If `None`, no maximum value constrain.

        """
        # If both minimum and maximum values are defined, ensure min_value <= max_value
        if (min_value is not None) and (max_value is not None) and (min_value > max_value):
            raise ArgumentError("minimum value is greater than maximum value")
        # Add lambda function to check numeric constrains when parsing argument
        kwargs["type"] = lambda x: self._validate_number(x, type, min_value, max_value)
        self.add_argument(*args, **kwargs)

    # pylint: disable=redefined-builtin
    def add_server_arguments(
        self, prefix: str = "", include_database: bool = False, help: str | None = None
    ) -> None:
        """Adds the usual set of arguments needed to connect to a server, i.e. `--host`, `--port`, `--user`
        and `--password` (optional).

        Note that the parser will assume this is a MySQL server.

        Args:
            prefix: Prefix to add the each argument, e.g. if prefix is `src_`, the arguments will be
                `--src_host`, etc.
            include_database: Include `--database` argument.
            help: Description message to include for this set of arguments.

        """
        group = self.add_argument_group(f"{prefix}server connection arguments", description=help)
        group.add_argument(
            f"--{prefix}host", required=True, metavar="HOST", default=argparse.SUPPRESS, help="host name"
        )
        group.add_argument(
            f"--{prefix}port",
            required=True,
            type=int,
            metavar="PORT",
            default=argparse.SUPPRESS,
            help="port number",
        )
        group.add_argument(
            f"--{prefix}user", required=True, metavar="USER", default=argparse.SUPPRESS, help="user name"
        )
        group.add_argument(f"--{prefix}password", metavar="PWD", help="host password")
        if include_database:
            group.add_argument(
                f"--{prefix}database",
                required=True,
                metavar="NAME",
                default=argparse.SUPPRESS,
                help="database name",
            )
        self.__server_groups.append(prefix)

    def add_log_arguments(self, add_log_file: bool = False) -> None:
        """Adds the usual set of arguments required to set and initialise a logging system.

        The current set includes a mutually exclusive group for the default logging level: `--verbose`,
        `--debug` or `--log LEVEL`.

        Args:
            add_log_file: Add arguments to allow storing messages into a file, i.e. `--log_file` and
                `--log_file_level`.

        """
        # Define the list of log levels available
        log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        # NOTE: from 3.11 this list can be changed to: logging.getLevelNamesMapping().keys()
        # Create logging arguments group
        group = self.add_argument_group("logging arguments")
        # Add 3 mutually exclusive options to set the logging level
        subgroup = group.add_mutually_exclusive_group()
        subgroup.add_argument(
            "-v",
            "--verbose",
            action="store_const",
            const="INFO",
            dest="log_level",
            help="verbose mode, i.e. 'INFO' log level",
        )
        subgroup.add_argument(
            "--debug",
            action="store_const",
            const="DEBUG",
            dest="log_level",
            help="debugging mode, i.e. 'DEBUG' log level",
        )
        subgroup.add_argument(
            "--log",
            choices=log_levels,
            type=str.upper,
            default="WARNING",
            metavar="LEVEL",
            dest="log_level",
            help="level of the events to track: %(choices)s",
        )
        subgroup.set_defaults(log_level="WARNING")
        if add_log_file:
            # Add log file-related arguments
            group.add_argument(
                "--log_file",
                type=lambda x: self._validate_dst_path(x, exists_ok=True),
                metavar="PATH",
                default=None,
                help="log file path",
            )
            group.add_argument(
                "--log_file_level",
                choices=log_levels,
                type=str.upper,
                default="DEBUG",
                metavar="LEVEL",
                help="level of the events to track in the log file: %(choices)s",
            )

    def parse_args(self, *args: Any, **kwargs: Any) -> argparse.Namespace:  # type: ignore[override]
        """Extends the parent function by adding a new URL argument for every server group added.

        The type of this new argument will be `sqlalchemy.engine.URL`. It also logs all the parsed
        arguments for debugging purposes when logging arguments have been added.

        """
        arguments = super().parse_args(*args, **kwargs)
        # Build and add an sqlalchemy.engine.URL object for every server group added
        for prefix in self.__server_groups:
            # Raise an error rather than overwriting when the URL argument is already present
            if f"{prefix}url" in arguments:
                self.error(f"argument '{prefix}url' is already present")
            server_url = URL.create(
                "mysql",
                getattr(arguments, f"{prefix}user"),
                getattr(arguments, f"{prefix}password"),
                getattr(arguments, f"{prefix}host"),
                getattr(arguments, f"{prefix}port"),
                getattr(arguments, f"{prefix}database", None),
            )
            setattr(arguments, f"{prefix}url", server_url)
        return arguments
