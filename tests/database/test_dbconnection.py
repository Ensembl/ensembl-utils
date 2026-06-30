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

from pathlib import Path

import pytest
from pytest import FixtureRequest, param
from sqlalchemy_utils import create_database, database_exists, drop_database
from sqlalchemy import Integer, text, Sequence, String
from sqlalchemy.orm import Mapped
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.automap import automap_base

# Support both SQLAlchemy 1.4+ and 2.0+
try:
    from sqlalchemy.orm import DeclarativeBase, mapped_column

    class MockBase(DeclarativeBase):
        """Mock Base for testing."""

except ImportError:
    from sqlalchemy.orm import declarative_base
    from sqlalchemy.schema import Column as mapped_column  # type: ignore

    MockBase = declarative_base()  # type: ignore

from ensembl.utils.database import DBConnection, UnitTestDB
from ensembl.utils.database.unittestdb import TEST_USERNAME


class MockTable(MockBase):
    """Mock Table for testing."""

    __tablename__ = "mock_table"

    id: Mapped[int] = mapped_column(Integer, Sequence("id_seq"), primary_key=True)
    grp: Mapped[str] = mapped_column(String(30))
    value: Mapped[int] = mapped_column(Integer)


mock_metadata = MockBase.metadata


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
        expected_db_name = f"{TEST_USERNAME}_mock_db"
        if self.dbc.dialect == "sqlite":
            expected_db_name += ".db"
        assert self.dbc.db_name == expected_db_name

    @pytest.mark.dependency(depends=["test_init", "test_dialect", "test_db_name"], scope="class")
    def test_url(self) -> None:
        """Tests `DBConnection.url` property."""
        expected_url = make_url(self.server).set(database=self.dbc.db_name)
        assert self.dbc.url == expected_url.render_as_string(hide_password=False)  # pylint: disable=no-member

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

    @pytest.mark.dependency(depends=["test_init", "test_connect"], scope="class")
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
        with self.dbc.session_scope() as session:
            query = text(f"SELECT * FROM gibberish WHERE id = {identifier}")
            results = session.execute(query)
            assert len(results.fetchall()) == before

        # Session requires mapped classes to interact with the database
        Base = automap_base()
        with self.dbc.connect() as con:
            Base.prepare(autoload_with=con)
            Gibberish = Base.classes.gibberish

            # Ignore IntegrityError raised when committing the new tags as some parametrizations will force it
            try:
                with self.dbc.session_scope() as session:
                    rows = [Gibberish(id=identifier, **x) for x in rows_to_add]
                    session.add_all(rows)
            except IntegrityError:
                pass

        with self.dbc.session_scope() as session:
            results = session.execute(query)
            assert len(results.fetchall()) == after

    @pytest.mark.dependency(depends=["test_init", "test_connect"], scope="class")
    def test_test_session_scope(self) -> None:
        """Tests `DBConnection.test_session_scope()` method."""
        # Session requires mapped classes to interact with the database
        Base = automap_base()
        with self.dbc.connect() as con:
            Base.prepare(autoload_with=con)
            Gibberish = Base.classes.gibberish

        # First add some rows within a scope
        identifier = 8
        with self.dbc.test_session_scope() as session:
            results = session.query(Gibberish).filter_by(id=identifier)
            assert not results.all(), f"ID {identifier} should not have any entries"
            session.add(Gibberish(id=identifier, grp="grp7", value=15))
            session.add(Gibberish(id=identifier, grp="grp8", value=25))
            session.commit()
            results = session.query(Gibberish).filter_by(id=identifier)
            assert len(results.all()) == 2, f"ID {identifier} should have two rows"

        # Check that the tags added during the previous scope have been removed
        with self.dbc.test_session_scope() as session:
            results = session.execute(text(f"SELECT * FROM gibberish WHERE id = {identifier}"))
            if (
                self.dbc.dialect == "mysql"
                and self.dbc.tables["gibberish"].dialect_options["mysql"]["engine"] == "MyISAM"
            ):
                assert len(results.all()) == 2, f"MyISAM: 2 rows permanently added to ID {identifier}"
            else:
                assert (
                    not results.fetchall()
                ), f"No entries should have been permanently added to ID {identifier}"


@pytest.mark.parametrize(
    "reflect, tables",
    [
        param(True, set(["gibberish"]), id="With reflection"),
        param(False, set(), id="No reflection"),
    ],
)
def test_reflect(request: FixtureRequest, data_dir: Path, reflect: bool, tables: set) -> None:
    """Tests the object `DBConnection` with and without reflection."""

    # Create a test db
    server_url = request.config.getoption("server")
    test_db = UnitTestDB(server_url, dump_dir=data_dir / "mock_db")
    test_db_url = test_db.dbc.url
    con = DBConnection(test_db_url, reflect=reflect)
    assert set(con.tables.keys()) == tables


def test_create_all_tables(request: FixtureRequest) -> None:
    """Tests the method `DBConnection.create_all_tables()`."""

    # Create a test db
    db_url = make_url(request.config.getoption("server"))
    db_name = f"{TEST_USERNAME}_test_create_all_tables"
    db_url = db_url.set(database=db_name)
    if database_exists(db_url):
        drop_database(db_url)
    create_database(db_url)

    try:
        test_db = DBConnection(db_url, reflect=False)
        test_db.create_all_tables(mock_metadata)
        assert set(test_db.tables.keys()) == set(mock_metadata.tables.keys())
    finally:
        drop_database(db_url)


def test_create_table(request: FixtureRequest) -> None:
    """Tests the method `DBConnection.create_table()`."""

    # Create a test db
    db_url = make_url(request.config.getoption("server"))
    db_name = f"{TEST_USERNAME}_test_create_table"
    db_url = db_url.set(database=db_name)
    if database_exists(db_url):
        drop_database(db_url)
    create_database(db_url)

    try:
        test_db = DBConnection(db_url, reflect=False)
        test_db.create_table(mock_metadata.tables["mock_table"])
        assert set(test_db.tables.keys()) == set(["mock_table"])
    finally:
        drop_database(db_url)
