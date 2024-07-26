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
"""Unit testing of `ensembl.utils.database.unittestdb` module."""

from contextlib import nullcontext as does_not_raise
from pathlib import Path
from typing import ContextManager, Optional

import pytest
from pytest import FixtureRequest, param, raises
from sqlalchemy_utils.functions import database_exists
from sqlalchemy import Integer, text, Sequence, String
from sqlalchemy.orm import Mapped
from sqlalchemy.schema import MetaData

# Support both SQLAlchemy 1.4+ and 2.0+
try:
    from sqlalchemy.orm import DeclarativeBase, mapped_column

    class MockBase(DeclarativeBase):
        """Mock Base for testing."""

except ImportError:
    from sqlalchemy.orm import declarative_base
    from sqlalchemy.schema import Column as mapped_column  # type: ignore

    MockBase = declarative_base()  # type: ignore

from ensembl.utils.database import UnitTestDB


class MockTable(MockBase):
    """Mock Table for testing."""

    __tablename__ = "mock_table"

    id: Mapped[int] = mapped_column(Integer, Sequence("id_seq"), primary_key=True)
    grp: Mapped[str] = mapped_column(String(30))
    value: Mapped[int] = mapped_column(Integer)


mock_metadata = MockBase.metadata


class TestUnitTestDB:
    """Tests `UnitTestDB` class."""

    def test_drop(self, request: FixtureRequest, tmp_path: Path) -> None:
        """Tests the `UnitTestDB.drop()` method."""
        server_url = request.config.getoption("server")
        db = UnitTestDB(server_url, tmp_path=tmp_path, name="test_drop")
        db_url = db.dbc.url
        assert database_exists(db_url)
        db.drop()
        assert not database_exists(db_url)

    @pytest.mark.parametrize(
        "src, name, expectation",
        [
            param(Path("mock_db"), None, does_not_raise(), id="Default test database creation"),
            param(Path("mock_db"), "renamed_db", does_not_raise(), id="Rename test database"),
            param(Path("mock_dir"), None, raises(FileNotFoundError), id="Wrong dump folder"),
        ],
    )
    def test_init(
        self,
        request: FixtureRequest,
        data_dir: Path,
        tmp_path: Path,
        src: Path,
        name: Optional[str],
        expectation: ContextManager,
    ) -> None:
        """Tests that the object `UnitTestDB` is initialised correctly.

        Args:
            request: Fixture that provides information of the requesting test function.
            data_dir: Fixture that provides the path to the test data folder matching the test's name.
            src: Directory path with the database schema and one TSV data file per table.
            name: Name to give to the new database.
            expectation: Context manager for the expected exception.

        """
        with expectation:
            server_url = request.config.getoption("server")
            src_path = src if src.is_absolute() else data_dir / src
            with UnitTestDB(server_url, dump_dir=src_path, name=name, tmp_path=tmp_path) as test_db:
                # Check that the database has been created correctly
                assert test_db, "UnitTestDB should not be empty"
                assert test_db.dbc, "UnitTestDB's database connection should not be empty"
                # Check that the database has been loaded correctly from the dump files
                with test_db.dbc.test_session_scope() as session:
                    result = session.execute(text("SELECT * FROM gibberish"))
                    assert len(result.fetchall()) == 6, "Unexpected number of rows found in 'gibberish' table"

    @pytest.mark.parametrize(
        "metadata, tables",
        [
            param(None, [], id="Create database without schema"),
            param(mock_metadata, ["mock_table"], id="Create database from mock_metadata"),
        ],
    )
    def test_metadata(
        self,
        request: FixtureRequest,
        tmp_path: Path,
        tables: list,
        metadata: MetaData,
    ) -> None:
        """Tests that the `UnitTestDB` can load the schema from metadata.

        Args:
            request: Fixture that provides information of the requesting test function.
            tmp_path: Temp testing folder where a test db will be stored (if file based).
            tables: List of tables expected to be loaded in the database from the metadata.
            metadata: SQLAlchemy Metadata representation of the tables to load.

        """
        server_url = request.config.getoption("server")
        with UnitTestDB(server_url, metadata=metadata, tmp_path=tmp_path, name="test_metadata") as test_db:
            assert test_db, "UnitTestDB should not be empty"
            assert test_db.dbc, "UnitTestDB's database connection should not be empty"
            assert set(test_db.dbc.tables.keys()) == set(tables), "Loaded tables as expected"
