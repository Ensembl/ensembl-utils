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
"""Unit testing of `ensembl.utils.plugin` module.

Since certain elements are embedded within pytest itself, only the fixtures are unit tested in this case.
"""

from contextlib import nullcontext as does_not_raise
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, ContextManager
from unittest.mock import patch

import pytest
from pytest import FixtureRequest, param, raises

from ensembl.utils import StrPath
from ensembl.utils.database import StrURL


@dataclass
class MockTestDB:
    """Mocks `UnitTestDB` class by just storing the three arguments provided."""

    server_url: StrURL
    dump_dir: StrPath
    name: str

    def drop(self) -> None:
        """Mocks `UnitTestDB.drop()` method."""


@pytest.mark.dependency(name="test_data_dir")
def test_data_dir(request: FixtureRequest, data_dir: Path) -> None:
    """Tests the `data_dir` fixture.

    Args:
        request: Fixture that provides information of the requesting test function.
        data_dir: Fixture that provides the path to the test data folder matching the test's name.

    """
    assert data_dir.stem == request.path.stem


@pytest.mark.dependency(depends=["test_data_dir"])
@pytest.mark.parametrize(
    "left, right, expectation",
    [
        param("file1.txt", "file1.txt", does_not_raise(), id="Files are equal"),
        param("file1.txt", "file2.txt", raises(AssertionError), id="Files differ"),
    ],
)
def test_assert_files(
    assert_files: Callable, data_dir: Path, left: str, right: str, expectation: ContextManager
) -> None:
    """Tests the `assert_files` fixture.

    Args:
        assert_files: Fixture that provides an assertion function to compare two files.
        data_dir: Fixture that provides the path to the test data folder matching the test's name.
        left: Left file to compare.
        right: Right file to compare.
        expectation: Context manager for the expected exception.

    """
    with expectation:
        assert_files(data_dir / left, data_dir / right)


@pytest.mark.parametrize(
    "dump_dir, db_name",
    [
        (Path("dump_dir"), "dump_dir"),
        (Path("dump_dir").resolve(), "test_db"),
    ],
)
@patch("ensembl.utils.plugin.UnitTestDB", new=MockTestDB)
def test_db_factory(request: FixtureRequest, db_factory: Callable, dump_dir: Path, db_name: str) -> None:
    """Tests the `db_factory` fixture.

    Args:
        request: Fixture that provides information of the requesting test function.
        db_factory: Fixture that provides a unit test database factory.
        dump_dir: Directory path where the test database schema and content files are located.
        db_name: Name to give to the new database.

    """
    test_db = db_factory(dump_dir, db_name)
    assert test_db.server_url == request.config.getoption("server")
    assert test_db.name == db_name
    if dump_dir.is_absolute():
        assert test_db.dump_dir == dump_dir
    else:
        assert test_db.dump_dir.stem == str(dump_dir)
