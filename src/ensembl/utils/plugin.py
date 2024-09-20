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
"""Ensembl's pytest plugin with useful unit testing hooks and fixtures."""

from __future__ import annotations

from difflib import unified_diff
import os
from pathlib import Path
import re
from typing import Callable, Generator, TypeAlias

import pytest
from pytest import Config, FixtureRequest, Parser
from sqlalchemy.schema import MetaData

from ensembl.utils import StrPath
from ensembl.utils.database import UnitTestDB


DBFactory: TypeAlias = Callable[[StrPath | None, str | None, MetaData | None], UnitTestDB]


def pytest_addoption(parser: Parser) -> None:
    """Registers argparse-style options for Ensembl's unit testing.

    `Pytest initialisation hook
    <https://docs.pytest.org/en/latest/reference.html#_pytest.hookspec.pytest_addoption>`_.

    Args:
        parser: Parser for command line arguments and ini-file values.

    """
    # Add the Ensembl unitary test parameters to pytest parser
    group = parser.getgroup("Ensembl unit testing")
    group.addoption(
        "--server",
        action="store",
        metavar="URL",
        dest="server",
        required=False,
        default=os.getenv("DB_HOST", "sqlite:///"),
        help="Server URL where to create the test database(s)",
    )
    group.addoption(
        "--keep-dbs",
        action="store_true",
        dest="keep_dbs",
        required=False,
        help="Do not remove the test databases (default: False)",
    )


def pytest_report_header(config: Config) -> str:
    """Presents extra information in the report header.

    Args:
        config: Access to configuration values, pluginmanager and plugin hooks.

    """
    # Show server information, masking the password value
    server = config.getoption("server")
    server = re.sub(r"(//[^/]+:).*(@)", r"\1xxxxxx\2", server)
    return f"server: {server}"


@pytest.fixture(name="data_dir", scope="module")
def local_data_dir(request: FixtureRequest) -> Path:
    """Returns the path to the test data folder matching the test's name.

    Args:
        request: Fixture that provides information of the requesting test function.

    """
    return Path(request.module.__file__).with_suffix("")


@pytest.fixture(name="assert_files")
def fixture_assert_files() -> Callable[[StrPath, StrPath], None]:
    """Returns a function that asserts if two text files are equal, or prints their differences."""

    def _assert_files(result_path: StrPath, expected_path: StrPath) -> None:
        """Asserts if two files are equal, or prints their differences.

        Args:
            result_path: Path to results (test-made) file.
            expected_path: Path to expected file.

        """
        with open(result_path, "r") as result_fh:
            results = result_fh.readlines()
        with open(expected_path, "r") as expected_fh:
            expected = expected_fh.readlines()
        files_diff = list(
            unified_diff(
                results,
                expected,
                fromfile=f"Test-made file {Path(result_path).name}",
                tofile=f"Expected file {Path(expected_path).name}",
            )
        )
        assert_message = f"Test-made and expected files differ\n{' '.join(files_diff)}"
        assert len(files_diff) == 0, assert_message

    return _assert_files


@pytest.fixture(name="db_factory", scope="module")
def fixture_db_factory(request: FixtureRequest, data_dir: Path) -> Generator[DBFactory, None, None]:
    """Yields a unit test database factory.

    Args:
        request: Fixture that provides information of the requesting test function.
        data_dir: Fixture that provides the path to the test data folder matching the test's name.

    """
    created: dict[str, UnitTestDB] = {}
    server_url = request.config.getoption("server")

    def _db_factory(
        src: StrPath | None, name: str | None = None, metadata: MetaData | None = None
    ) -> UnitTestDB:
        """Returns a unit test database.

        Args:
            src: Directory path where the test database schema and content files are located, if any.
            name: Name to give to the new database. See `UnitTestDB` for more information.
            metadata: SQLAlchemy ORM schema metadata to populate the schema of the test database.

        """
        if src is not None:
            src_path = Path(src)
            if not src_path.is_absolute():
                src_path = data_dir / src_path
            db_key = name if name else src_path.name
            dump_dir: Path | None = src_path if src_path.exists() else None
        else:
            db_key = name if name else "dbkey"
            dump_dir = None
        return created.setdefault(
            db_key, UnitTestDB(server_url, dump_dir=dump_dir, name=name, metadata=metadata)
        )

    yield _db_factory
    # Drop all unit test databases unless the user has requested to keep them
    if not request.config.getoption("keep_dbs"):
        for test_db in created.values():
            test_db.drop()


@pytest.fixture(scope="module")
def test_dbs(request: FixtureRequest, db_factory: Callable) -> dict[str, UnitTestDB]:
    """Returns a dictionary of unit test databases with the database name as key.

    Requires a list of dictionaries, each with keys `src` (mandatory), `name` (optional) and `metadata`
    (optional), passed via `request.param`. See `db_factory()` for details about each key's value. This
    fixture is a wrapper of `db_factory()` intended to be used via indirect parametrization, for example::

        from ensembl.core.models import Base
        @pytest.mark.parametrize(
            "test_dbs",
            [
                [
                    {"src": "core_db"},
                    {"src": "core_db", "name": "human"},
                    {"src": "core_db", "name": "cat", "metadata": Base.metadata},
                ]
            ],
            indirect=True
        )
        def test_method(..., test_dbs: dict[str, UnitTestDB], ...):


    Args:
        request: Fixture that provides information of the requesting test function.
        db_factory: Fixture that provides a unit test database factory.

    """
    databases = {}
    for argument in request.param:
        src = argument.get("src", None)
        if src is not None:
            src = Path(src)
        name = argument.get("name", None)
        key = name if name else src.name
        databases[key] = db_factory(src=src, name=name, metadata=argument.get("metadata"))
    return databases
