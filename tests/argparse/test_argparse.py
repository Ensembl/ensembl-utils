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
"""Unit testing of `ensembl.utils.argparse` module."""

from contextlib import nullcontext as does_not_raise
from pathlib import Path
import re
from typing import Any, Callable, ContextManager

import pytest
from pytest import param, raises
from sqlalchemy.engine import make_url

from ensembl.utils.argparse import ArgumentError, ArgumentParser


def _args_dict_to_cmd_list(args_dict: dict[str, Any]) -> list[str]:
    """Returns a flattened version of the arguments dictionary in a list with every element as a string.

    It will add "--" to every key of the dictionary, and will not add empty values (for flag arguments).

    """
    cmd_args = []
    for key, value in args_dict.items():
        cmd_args.append(f"--{key}")
        if value:
            cmd_args.append(str(value))
    return cmd_args


class TestArgumentParser:
    """Tests `ArgumentParser` class."""

    def test_validate_unreadable_src_path(self, tmp_path: Path) -> None:
        """Tests `ArgumentParser._validate_src_path()` method for an unreadable file.

        Args:
            tmp_path: Fixture that provides a temporary directory path unique to the test invocation.

        """
        # Create file and make it unreadable
        src_path = tmp_path / "forbidden.txt"
        with src_path.open("w") as in_file:
            in_file.write("you shall not read this")
        src_path.chmod(0o222)
        # Attempt to validate source path
        parser = ArgumentParser()
        with raises(SystemExit):
            parser._validate_src_path(src_path)  # pylint: disable=protected-access

    @pytest.mark.parametrize(
        "is_dir",
        [
            param(True, id="Destination path is a file"),
            param(False, id="Destination path is a directory"),
        ],
    )
    def test_validate_unwritable_dst_path(self, tmp_path: Path, is_dir: bool) -> None:
        """Tests `ArgumentParser._validate_dst_path()` method for an unwritable path.

        Args:
            tmp_path: Fixture that provides a temporary directory path unique to the test invocation.
            is_dir: Make the unwritable destination path a directory (`True`) or file (`False`).

        """
        # Create a file or directory and make it unreadable
        if is_dir:
            dst_path = tmp_path / "read-only" / "read-only.txt"
            dst_path.parent.mkdir(mode=0o555)
        else:
            dst_path = tmp_path / "read-only.txt"
            with dst_path.open("w") as in_file:
                in_file.write("you shall not edit this")
            dst_path.chmod(0o444)
        # Attempt to validate source path
        parser = ArgumentParser()
        with raises(SystemExit):
            parser._validate_dst_path(dst_path)  # pylint: disable=protected-access

    @pytest.mark.dependency(name="add_argument")
    @pytest.mark.parametrize(
        "required",
        [
            param(True, id="Add required argument"),
            param(False, id="Add optional argument"),
        ],
    )
    def test_add_argument(self, required: bool) -> None:
        """Tests `ArgumentParser.add_argument()` method.

        Args:
            required: Set argument as required (`True`) or optional (`False`).

        """
        parser = ArgumentParser()
        parser.add_argument("--foo", help="text", required=required)
        if required:
            pattern = re.compile(r" +--foo FOO +text")
        else:
            pattern = re.compile(r" +--foo FOO +text \(default: None\)")
        assert pattern.search(parser.format_help()) is not None

    @pytest.mark.dependency(depends=["add_argument"])
    @pytest.mark.parametrize(
        "src_path, expectation",
        [
            param("", does_not_raise(), id="Optional input file"),
            param("sample.txt", does_not_raise(), id="Input file exists"),
            param("invalid.txt", raises(SystemExit), id="Input file does not exist"),
        ],
    )
    def test_add_argument_src_path(self, data_dir: Path, src_path: str, expectation: ContextManager) -> None:
        """Tests `ArgumentParser.add_argument_src_path()` method.

        Args:
            data_dir: Fixture that provides the path to the test data folder matching the test's name.
            src_path: Input file name.
            expectation: Context manager for the expected exception.

        """
        # Add "--src_path" argument to the parser and its command line
        parser = ArgumentParser()
        parser.add_argument_src_path("--src_path")
        cmd_args = ["--src_path", str(data_dir / src_path)]
        # Check that the argument is properly parsed
        with expectation:
            args = parser.parse_args(cmd_args)
            assert args.src_path == data_dir / src_path

    @pytest.mark.dependency(depends=["add_argument"])
    @pytest.mark.parametrize(
        "dst_path, exists_ok, expectation",
        [
            param("", True, does_not_raise(), id="Dir exists and writable, exists_ok = True"),
            param("", False, raises(SystemExit), id="Dir exists and writable, exists_ok = False"),
            param("output", True, does_not_raise(), id="Dir does not exist but parent is writable"),
            param("dir1/dir2", True, does_not_raise(), id="Dir does not exist but grandparent is writable"),
        ],
    )
    def test_add_argument_dst_path(
        self, data_dir: Path, dst_path: str, exists_ok: bool, expectation: ContextManager
    ) -> None:
        """Tests `ArgumentParser.add_argument_dst_path()` method.

        Args:
            data_dir: Fixture that provides the path to the test data folder matching the test's name.
            dst_path: Relative path to destination directory/file.
            exists_ok: Do not raise an error if the destination path already exists.
            expectation: Context manager for the expected exception.

        """
        # Add "--dst_path" argument to the parser and its command line
        parser = ArgumentParser()
        parser.add_argument_dst_path("--dst_path", exists_ok=exists_ok)
        cmd_args = ["--dst_path", str(data_dir / dst_path)]
        # Check that the argument is properly parsed
        with expectation:
            args = parser.parse_args(cmd_args)
            assert args.dst_path == data_dir / dst_path

    @pytest.mark.dependency(depends=["add_argument"])
    def test_add_argument_url(self) -> None:
        """Tests `ArgumentParser.add_argument_url()` method."""
        # Add "--url" argument to the parser and its command line
        parser = ArgumentParser()
        parser.add_argument_url("--url")
        cmd_args = ["--url", "https://github.com"]
        # Check that the argument is properly parsed
        args = parser.parse_args(cmd_args)
        assert args.url == make_url("https://github.com")

    @pytest.mark.dependency(depends=["add_argument"])
    @pytest.mark.parametrize(
        "value, value_type, min_value, max_value, expectation",
        [
            param("3", int, None, None, does_not_raise(), id="Value has expected type"),
            param("3", int, 3, 3, does_not_raise(), id="Value equal to minimum and maximum values"),
            param("3.5", float, 3.4, 3.6, does_not_raise(), id="Value within range"),
            param("3", int, 3, 2, raises(ArgumentError), id="Minimum value greater than maximum value"),
            param("3.2", int, None, None, raises(SystemExit), id="Value has incorrect type"),
            param("3", int, 4, None, raises(SystemExit), id="Value lower than minimum value"),
            param("3", int, None, 2, raises(SystemExit), id="Value greater than maximum value"),
        ],
    )
    def test_add_numeric_argument(
        self,
        value: str,
        value_type: Callable[[str], int | float],
        min_value: int | float | None,
        max_value: int | float | None,
        expectation: ContextManager,
    ) -> None:
        """Tests `ArgumentParser.add_numeric_argument()` method.

        Args:
            value: Argument value.
            value_type: Expected argument type.
            min_value: Minimum value constrain. If `None`, no minimum value constrain.
            max_value: Maximum value constrain. If `None`, no maximum value constrain.
            expectation: Context manager for the expected exception.

        """
        parser = ArgumentParser()
        # Add numeric argument to parser and its command line, and check that the argument is properly parsed
        with expectation:
            parser.add_numeric_argument("--num", type=value_type, min_value=min_value, max_value=max_value)
            cmd_args = ["--num", value]
            args = parser.parse_args(cmd_args)
            assert args.num == value_type(value)

    @pytest.mark.dependency(name="add_server_arguments", depends=["add_argument"])
    @pytest.mark.parametrize(
        "prefix, include_database",
        [
            param("", False, id="Basic call"),
            param("src", False, id="Add prefix"),
            param("", True, id="Add database argument"),
        ],
    )
    def test_add_server_arguments(self, prefix: str, include_database: bool) -> None:
        """Tests `ArgumentParser.add_server_arguments()` method.

        Args:
            prefix: Prefix to add the each argument.
            include_database: Include `--database` argument.

        """
        # Add server arguments to the parser and its command line
        parser = ArgumentParser()
        parser.add_server_arguments(prefix=prefix, include_database=include_database)
        cmd_args = {
            f"{prefix}host": "lugh",
            f"{prefix}port": 42,
            f"{prefix}user": "username",
            f"{prefix}password": "***",
        }
        url = "mysql://username:***@lugh:42"
        if include_database:
            cmd_args[f"{prefix}database"] = "my_db"
            url += "/my_db"
        # Check that the arguments are properly parsed
        args = parser.parse_args(_args_dict_to_cmd_list(cmd_args))
        for arg_name, value in cmd_args.items():
            assert getattr(args, arg_name) == value
        assert getattr(args, f"{prefix}url") == make_url(url)

    @pytest.mark.dependency(depends=["add_argument"])
    @pytest.mark.parametrize(
        "add_log_file, cmd_args, log_level",
        [
            param(False, {}, "WARNING", id="Default configuration"),
            param(False, {"log": "ERROR"}, "ERROR", id="ERROR log level"),
            param(False, {"debug": ""}, "DEBUG", id="DEBUG log level"),
            param(False, {"verbose": ""}, "INFO", id="INFO log level"),
            param(
                True,
                {"log_file": Path("app.log"), "log_file_level": "ERROR"},
                "WARNING",
                id="Add log file",
            ),
        ],
    )
    def test_add_log_arguments(self, add_log_file: bool, cmd_args: dict[str, Any], log_level: str) -> None:
        """Tests `ArgumentParser.add_log_arguments()` method.

        Args:
            add_log_file: Add arguments to allow storing messages into a file.
            cmd_args: Command line arguments to pass to the parser.
            log_level: Logging level expected.

        """
        # Add log arguments to the parser and its command line
        parser = ArgumentParser()
        parser.add_log_arguments(add_log_file=add_log_file)
        # Check that the argument is properly parsed
        args = parser.parse_args(_args_dict_to_cmd_list(cmd_args))
        assert args.log_level == log_level
        if add_log_file:
            for arg_name, value in cmd_args.items():
                assert getattr(args, arg_name) == value

    @pytest.mark.dependency(depends=["add_server_arguments"])
    def test_parse_args(self) -> None:
        """Tests `ArgumentParser.parse_args()` method.

        The only check left is when server arguments and a URL argument all with the same prefix
        are added to the parser.

        """
        # Add server arguments with prefix "src" and URL argument with the same prefix to the parser
        parser = ArgumentParser()
        parser.add_server_arguments("src_")
        parser.add_argument_url("--src_url")
        # Check that the error is handled properly
        with raises(SystemExit):
            parser.parse_args(["--src_host", "host", "--src_port", "42", "--src_user", "username"])
