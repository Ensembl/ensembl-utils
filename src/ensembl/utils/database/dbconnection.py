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
"""Database connection handler.

This module provides the main class to connect to and access databases. It will be an ORM-less
connection, that is, the data can only be accessed via SQL queries (see example below).

Examples:

    >>> from ensembl.utils.database import DBConnection
    >>> dbc = DBConnection("mysql://ensro@mysql-server:4242/mydb")
    >>> # You can access the database data via sql queries, for instance:
    >>> results = dbc.execute("SELECT * FROM my_table;")
    >>> # Or via a connection in a transaction manner:
    >>> with dbc.begin() as conn:
    >>>     results = conn.execute("SELECT * FROM my_table;")

"""

from __future__ import annotations

__all__ = [
    "Query",
    "StrURL",
    "DBConnection",
]

from contextlib import contextmanager
from typing import Any, ContextManager, Generator, Optional, TypeVar

import sqlalchemy
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import MetaData, Table


Query = TypeVar("Query", str, sqlalchemy.sql.expression.ClauseElement, sqlalchemy.sql.expression.TextClause)
StrURL = TypeVar("StrURL", str, sqlalchemy.engine.URL)


class DBConnection:
    """Database connection handler, providing also the database's schema and properties.

    Args:
        url: URL to the database, e.g. `mysql://user:passwd@host:port/my_db`.
        reflect: Reflect the database schema or not.

    """

    def __init__(self, url: StrURL, reflect: bool = True, **kwargs: Any) -> None:
        self._engine = create_engine(url, future=True, **kwargs)
        self._metadata: MetaData | None = None
        if reflect:
            self.load_metadata()

    def __repr__(self) -> str:
        """Returns a string representation of this object."""
        return f"{self.__class__.__name__}({self.url!r})"

    def load_metadata(self) -> None:
        """Loads the metadata information of the database."""
        # Note: Just reflect() is not enough as it would not delete tables that no longer exist
        self._metadata = sqlalchemy.MetaData()
        self._metadata.reflect(bind=self._engine)

    def create_all_tables(self, metadata: MetaData) -> None:
        """Create the tables from the metadata and set the metadata.

        This assumes the database is empty beforehand. If the tables already exist, they will be ignored.
        If there are other tables, you may need to run `self.load_metadata()` to update the metadata schema.
        """
        self._metadata = metadata
        metadata.create_all(self._engine)

    def create_table(self, table: Table) -> None:
        """Create a table in the database and update the metadata. Do nothing if the table already exists."""
        table.create(self._engine)
        # We need to update the metadata to register the new table
        self.load_metadata()

    @property
    def url(self) -> str:
        """Returns the database URL."""
        return self._engine.url.render_as_string(hide_password=False)

    @property
    def db_name(self) -> Optional[str]:
        """Returns the database name."""
        return self._engine.url.database

    @property
    def host(self) -> Optional[str]:
        """Returns the database host."""
        return self._engine.url.host

    @property
    def port(self) -> Optional[int]:
        """Returns the port of the database host."""
        return self._engine.url.port

    @property
    def dialect(self) -> str:
        """Returns the SQLAlchemy database dialect name of the database host."""
        return self._engine.name

    @property
    def tables(self) -> dict[str, sqlalchemy.schema.Table]:
        """Returns the database tables keyed to their name, or an empty dict if no metadata was loaded."""
        if self._metadata:
            return self._metadata.tables
        return {}

    def get_primary_key_columns(self, table: str) -> list[str]:
        """Returns the primary key column names for the given table.

        Args:
            table: Table name.

        """
        return [col.name for col in self.tables[table].primary_key.columns.values()]

    def get_columns(self, table: str) -> list[str]:
        """Returns the column names for the given table.

        Args:
            table: Table name.

        """
        return [col.name for col in self.tables[table].columns]

    def connect(self) -> sqlalchemy.engine.Connection:
        """Returns a new database connection."""
        return self._engine.connect()

    def begin(self, *args: Any) -> ContextManager[sqlalchemy.engine.Connection]:
        """Returns a context manager delivering a database connection with a transaction established."""
        return self._engine.begin(*args)

    def dispose(self) -> None:
        """Disposes of the connection pool."""
        self._engine.dispose()

    def _enable_sqlite_savepoints(self, engine: sqlalchemy.engine.Engine) -> None:
        """Enables SQLite SAVEPOINTS to allow session rollbacks."""

        @event.listens_for(engine, "connect")
        def do_connect(
            dbapi_connection: Any,  # SQLAlchemy is not clear about the type of this argument
            connection_record: sqlalchemy.pool.ConnectionPoolEntry,  # pylint: disable=unused-argument
        ) -> None:
            """Disables emitting the BEGIN statement entirely, as well as COMMIT before any DDL."""
            dbapi_connection.isolation_level = None

        @event.listens_for(engine, "begin")
        def do_begin(conn: sqlalchemy.engine.Connection) -> None:
            """Emits a custom own BEGIN."""
            conn.exec_driver_sql("BEGIN")

    @contextmanager
    def session_scope(self) -> Generator[sqlalchemy.orm.Session, None, None]:
        """Provides a transactional scope around a series of operations with rollback in case of failure.

        Bear in mind MySQL's storage engine MyISAM does not support rollback transactions, so all
        the modifications performed to the database will persist.

        """
        # Create a dedicated engine for this session
        engine = create_engine(self._engine.url)
        if self.dialect == "sqlite":
            self._enable_sqlite_savepoints(engine)
        Session = sessionmaker(future=True)
        session = Session(bind=engine, autoflush=False)
        try:
            yield session
            session.commit()
        except:
            # Rollback to ensure no changes are made to the database
            session.rollback()
            raise
        finally:
            # Whatever happens, make sure the session is closed
            session.close()

    @contextmanager
    def test_session_scope(self) -> Generator[sqlalchemy.orm.Session, None, None]:
        """Provides a transactional scope around a series of operations that will be rolled back at the end.

        Bear in mind MySQL's storage engine MyISAM does not support rollback transactions, so all
        the modifications performed to the database will persist.

        """
        # Create a dedicated engine for this session
        engine = create_engine(self._engine.url)
        if self.dialect == "sqlite":
            self._enable_sqlite_savepoints(engine)
        # Connect to the database
        connection = engine.connect()
        # Begin a non-ORM transaction
        transaction = connection.begin()
        # Bind an individual session to the connection
        Session = sessionmaker(future=True)
        try:
            # Running on SQLAlchemy 2.0+
            session = Session(bind=connection, join_transaction_mode="create_savepoint")
        except TypeError:
            # Running on SQLAlchemy 1.4
            session = Session(bind=connection)
            # If the database supports SAVEPOINT, starting a savepoint will allow to also use rollback
            connection.begin_nested()

            # Define a new transaction event
            @event.listens_for(session, "after_transaction_end")
            def end_savepoint(
                session: sqlalchemy.orm.Session,  # pylint: disable=unused-argument
                transaction: sqlalchemy.orm.SessionTransaction,  # pylint: disable=unused-argument
            ) -> None:
                if not connection.in_nested_transaction():
                    connection.begin_nested()

        try:
            yield session
        finally:
            # Whatever happens, make sure the session and connection are closed, rolling back
            # everything done with the session (including calls to commit())
            session.close()
            transaction.rollback()
            connection.close()
