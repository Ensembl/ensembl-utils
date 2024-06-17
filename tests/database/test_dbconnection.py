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
"""Unit testing of `ensembl.utils.database.dbconnection` module."""

from contextlib import nullcontext as does_not_raise
import os
from typing import ContextManager

import pytest
from pytest import FixtureRequest, param, raises
from sqlalchemy import text
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.automap import automap_base

from ensembl.utils.database import DBConnection, Query, UnitTestDB


@pytest.mark.parametrize("test_dbs", [[{"src": "mock_db"}]], indirect=True)
class TestDBConnection:
    """Tests `DBConnection` class.

    Attributes:
        dbc: Test database connection.
        server: Server URL where the test database is hosted.

    """

    dbc: DBConnection = None
    server: str = ""

    @pytest.fixture(scope="class", autouse=True)
    @classmethod
    def setup(cls, request: FixtureRequest, test_dbs: dict[str, UnitTestDB]) -> None:
        """Loads the required fixtures and values as class attributes.

        Args:
            request: Fixture that provides information of the requesting test function.
            test_dbs: Fixture that provides the unit test databases.

        """
        cls.dbc = test_dbs["mock_db"].dbc
        cls.server = request.config.getoption("server")

    @pytest.mark.dependency(name="test_init", scope="class")
    def test_init(self) -> None:
        """Tests that the object `DBConnection` is initialised correctly."""
        assert self.dbc, "DBConnection object should not be empty"

    @pytest.mark.dependency(name="test_dialect", depends=["test_init"], scope="class")
    def test_dialect(self) -> None:
        """Tests `DBConnection.dialect` property."""
        assert self.dbc.dialect == make_url(self.server).drivername

    @pytest.mark.dependency(name="test_db_name", depends=["test_init", "test_dialect"], scope="class")
    def test_db_name(self) -> None:
        """Tests `DBConnection.db_name` property."""
        expected_db_name = f"{os.environ['USER']}_mock_db"
        if self.dbc.dialect == "sqlite":
            expected_db_name += ".db"
        assert self.dbc.db_name == expected_db_name

    @pytest.mark.dependency(depends=["test_init", "test_dialect", "test_db_name"], scope="class")
    def test_url(self) -> None:
        """Tests `DBConnection.url` property."""
        expected_url = make_url(self.server).set(database=self.dbc.db_name)
        assert self.dbc.url == expected_url.render_as_string(hide_password=False)

    @pytest.mark.dependency(depends=["test_init"], scope="class")
    def test_host(self) -> None:
        """Tests `DBConnection.host` property."""
        assert self.dbc.host == make_url(self.server).host

    @pytest.mark.dependency(depends=["test_init"], scope="class")
    def test_port(self) -> None:
        """Tests `DBConnection.port` property."""
        assert self.dbc.port == make_url(self.server).port

    @pytest.mark.dependency(depends=["test_init"], scope="class")
    def test_tables(self) -> None:
        """Tests `DBConnection.tables` property."""
        assert set(self.dbc.tables.keys()) == {"gibberish"}

    @pytest.mark.dependency(depends=["test_init"], scope="class")
    def test_get_primary_key_columns(self) -> None:
        """Tests `DBConnection.get_primary_key_columns()` method."""
        table = "gibberish"
        assert set(self.dbc.get_primary_key_columns(table)) == {
            "id",
            "grp",
        }, f"Unexpected set of primary key columns found in table '{table}'"

    @pytest.mark.dependency(depends=["test_init"], scope="class")
    def test_get_columns(self) -> None:
        """Tests `DBConnection.get_columns()` method."""
        table = "gibberish"
        assert set(self.dbc.get_columns(table)) == {
            "id",
            "grp",
            "value",
        }, f"Unexpected set of columns found in table '{table}'"

    @pytest.mark.dependency(name="test_connect", depends=["test_init"], scope="class")
    def test_connect(self) -> None:
        """Tests `DBConnection.connect()` method."""
        connection = self.dbc.connect()
        assert connection, "Connection object should not be empty"
        result = connection.execute(text("SELECT * FROM gibberish"))
        assert len(result.fetchall()) == 6, "Unexpected number of rows found in 'gibberish' table"
        connection.close()

    @pytest.mark.dependency(depends=["test_init"], scope="class")
    def test_begin(self) -> None:
        """Tests `DBConnection.begin()` method."""
        with self.dbc.begin() as connection:
            assert connection, "Connection object should not be empty"
            result = connection.execute(text("SELECT * FROM gibberish"))
            assert len(result.fetchall()) == 6, "Unexpected number of rows found in 'gibberish' table"

    @pytest.mark.dependency(depends=["test_init"], scope="class")
    def test_dispose(self) -> None:
        """Tests `DBConnection.dispose()` method."""
        self.dbc.dispose()
        # SQLAlchemy uses a "pool-less" connection system for SQLite
        if self.dbc.dialect != "sqlite":
            num_conn = self.dbc._engine.pool.checkedin()  # pylint: disable=protected-access
            assert num_conn == 0, "A new pool should have 0 checked-in connections"

    @pytest.mark.dependency(name="test_exec", depends=["test_init"], scope="class")
    @pytest.mark.parametrize(
        "query, nrows, expectation",
        [
            param("SELECT * FROM gibberish", 6, does_not_raise(), id="Valid string query"),
            param(text("SELECT * FROM gibberish"), 6, does_not_raise(), id="Valid text query"),
            param(
                "SELECT * FROM my_table",
                0,
                raises(SQLAlchemyError, match=r"(my_table.* doesn't exist|no such table: my_table)"),
                id="Querying an unexistent table",
            ),
        ],
    )
    def test_execute(self, query: Query, nrows: int, expectation: ContextManager) -> None:
        """Tests `DBConnection.execute()` method.

        Args:
            query: SQL query.
            nrows: Number of rows expected to be returned from the query.
            expectation: Context manager for the expected exception.

        """
        with expectation:
            result = self.dbc.execute(query)
            assert len(result.fetchall()) == nrows, "Unexpected number of rows returned"

    @pytest.mark.dependency(depends=["test_init", "test_connect", "test_exec"], scope="class")
    @pytest.mark.parametrize(
        "identifier, rows_to_add, before, after",
        [
            param(7, [{"grp": "grp4", "value": 1}, {"grp": "grp5", "value": 1}], 0, 2, id="Add new data"),
            param(
                7, [{"grp": "grp6", "value": 1}, {"grp": "grp6", "value": 2}], 2, 2, id="Add existing data"
            ),
        ],
    )
    def test_session_scope(
        self, identifier: int, rows_to_add: list[dict[str, str]], before: int, after: int
    ) -> None:
        """Tests `DBConnection.session_scope()` method.

        Bear in mind that the second parameterization of this test will fail if the dialect/table engine
        does not support rollback transactions.

        Args:
            identifier: ID of the rows to add.
            rows_to_add: Rows to add to the `gibberish` table.
            before: Number of rows in `gibberish` table for `id` before adding the rows.
            after: Number of rows in `gibberish` table for `id` after adding the rows.

        """
        query = f"SELECT * FROM gibberish WHERE id = {identifier}"
        results = self.dbc.execute(query)
        assert len(results.fetchall()) == before
        # Session requires mapped classes to interact with the database
        Base = automap_base()
        Base.prepare(autoload_with=self.dbc.connect())
        Gibberish = Base.classes.gibberish
        # Ignore IntegrityError raised when committing the new tags as some parametrizations will force it
        try:
            with self.dbc.session_scope() as session:
                rows = [Gibberish(id=identifier, **x) for x in rows_to_add]
                session.add_all(rows)
        except IntegrityError:
            pass
        results = self.dbc.execute(query)
        assert len(results.fetchall()) == after

    @pytest.mark.dependency(depends=["test_init", "test_connect", "test_exec"], scope="class")
    def test_test_session_scope(self) -> None:
        """Tests `DBConnection.test_session_scope()` method."""
        # Session requires mapped classes to interact with the database
        Base = automap_base()
        Base.prepare(autoload_with=self.dbc.connect())
        Gibberish = Base.classes.gibberish
        # Check that the tags added during the context manager are removed afterwards
        identifier = 8
        with self.dbc.test_session_scope() as session:
            results = session.query(Gibberish).filter_by(id=identifier)
            assert not results.all(), f"ID {identifier} should not have any entries"
            session.add(Gibberish(id=identifier, grp="grp7", value=15))
            session.add(Gibberish(id=identifier, grp="grp8", value=25))
            session.commit()
            results = session.query(Gibberish).filter_by(id=identifier)
            assert len(results.all()) == 2, f"ID {identifier} should have two rows"
        results = self.dbc.execute(f"SELECT * FROM gibberish WHERE id = {identifier}")
        if (
            self.dbc.dialect == "mysql"
            and self.dbc.tables["gibberish"].dialect_options["mysql"]["engine"] == "MyISAM"
        ):
            assert len(results.all()) == 2, f"SQLite/MyISAM: 2 rows permanently added to ID {identifier}"
        else:
            assert not results.fetchall(), f"No entries should have been permanently added to ID {identifier}"
