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
# pylint: disable=too-many-positional-arguments

from contextlib import nullcontext as does_not_raise
from pathlib import Path
from typing import Callable, ContextManager

import pytest
from pytest import FixtureRequest, param, raises
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.schema import MetaData

from ensembl.utils.database import UnitTestDB


class Base(DeclarativeBase):
    """Test DB with one table."""


class Foo(Base):
    """One test table."""

    __tablename__ = "foo"
    id: Mapped[int] = mapped_column(primary_key=True)


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
    "dump_dir, make_absolute, db_name, metadata, expected_db_name, expected_tables",
    [
        param(
            Path("dump_dir"), False, "rel_dump_db", None, "rel_dump_db", ["gibberish"], id="Relative dump_dir"
        ),
        param(Path("dump_dir"), False, "", None, "dump_dir", ["gibberish"], id="Relative dump_dir"),
        param(
            Path("dump_dir"), True, "abs_dump_db", None, "abs_dump_db", ["gibberish"], id="Absolute dump_dir"
        ),
        param(Path("not_a_dir"), False, "no_dump_db", None, "no_dump_db", [], id="Non-existent dump_dir"),
        param(Path("not_a_dir"), False, "metadata", Base.metadata, "metadata", ["foo"], id="Use metadata"),
        param(None, False, "named_empty_db", None, "named_empty_db", [], id="Named empty database"),
        param(None, False, "", None, "testdb", [], id="Unnamed empty database"),
    ],
)
def test_db_factory(
    request: FixtureRequest,
    db_factory: Callable[[Path | None, str | None, MetaData | None], UnitTestDB],
    data_dir: Path,
    dump_dir: Path | None,
    make_absolute: bool,
    db_name: str,
    metadata: MetaData | None,
    expected_db_name: str,
    expected_tables: list[str],
) -> None:
    """Tests the `db_factory` fixture.

    Args:
        request: Fixture that provides information of the requesting test function.
        db_factory: Fixture that provides a unit test database factory.
        data_dir: Directory where this specific test data are stored.
        dump_dir: Directory path where the test database schema and content files are located.
        make_absolute: change the dump_dir from relative to absolute (based on `data_dir`).
        db_name: Name to give to the new database.
        metadata: SQLAlchemy metadata to build a database from ORM instead of dump_dir.
        expected_db_name: Expected database name.
        expected_tables: List of tables that should be loaded in the test database.

    """
    if (dump_dir is not None) and make_absolute:
        dump_dir = Path(data_dir, dump_dir).absolute()
    test_db: UnitTestDB = db_factory(dump_dir, db_name, metadata)

    assert test_db.dbc.url.startswith(request.config.getoption("server"))
    assert Path(test_db.dbc.db_name).stem.endswith(expected_db_name)
    assert set(test_db.dbc.tables.keys()) == set(expected_tables)


@pytest.mark.parametrize(
    "test_dbs, expected_db_name",
    [
        param([{"name": "human"}], "human", id="Empty test database"),
        param([{"src": "dump_dir"}], "dump_dir", id="Basic test database"),
        param([{"src": "dump_dir", "name": "human"}], "human", id="Named test database"),
        param([{"src": "dump_dir", "metadata": Base.metadata}], "dump_dir", id="Declare metadata"),
    ],
    indirect=["test_dbs"],
)
def test_test_dbs(test_dbs: dict[str, UnitTestDB], expected_db_name: str) -> None:
    """Tests the `test_dbs` fixture."""
    assert expected_db_name in test_dbs
    assert test_dbs[expected_db_name].dbc is not None
