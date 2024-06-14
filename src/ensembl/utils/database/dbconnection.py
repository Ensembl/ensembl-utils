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
    "URL",
    "DBConnection",
]

import contextlib
from typing import TypeVar

import sqlalchemy
from sqlalchemy import create_engine, event, text


Query = TypeVar("Query", str, sqlalchemy.sql.expression.ClauseElement)
URL = TypeVar("URL", str, sqlalchemy.engine.url.URL)


class DBConnection:
    """Database connection handler, providing also the database's schema and properties.

    Args:
        url: URL to the database, e.g. `mysql://user:passwd@host:port/my_db`.

    """

    def __init__(self, url: URL, **kwargs) -> None:
        self._engine = create_engine(url, **kwargs)
        self.load_metadata()

    def __repr__(self) -> str:
        """Returns a string representation of this object."""
        return f"{self.__class__.__name__}({self.url!r})"

    def load_metadata(self) -> None:
        """Loads the metadata information of the database."""
        # Note: Just reflect() is not enough as it would not delete tables that no longer exist
        self._metadata = sqlalchemy.MetaData(bind=self._engine)
        self._metadata.reflect()

    @property
    def url(self) -> str:
        """Returns the database URL."""
        return str(self._engine.url)

    @property
    def db_name(self) -> str:
        """Returns the database name."""
        return self._engine.url.database

    @property
    def host(self) -> str:
        """Returns the database host."""
        return self._engine.url.host

    @property
    def port(self) -> int:
        """Returns the port of the database host."""
        return self._engine.url.port

    @property
    def dialect(self) -> str:
        """Returns the SQLAlchemy database dialect name of the database host."""
        return self._engine.name

    @property
    def tables(self) -> dict[str, sqlalchemy.schema.Table]:
        """Returns the database tables keyed to their name."""
        return self._metadata.tables

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

    def begin(self, *args) -> sqlalchemy.engine.Connection:
        """Returns a context manager delivering a database connection with a transaction established."""
        return self._engine.begin(*args)

    def dispose(self) -> None:
        """Disposes of the connection pool."""
        self._engine.dispose()

    def execute(self, statement: Query, *multiparams, **params) -> sqlalchemy.engine.Result:
        """Executes the given SQL query and returns its result.

        Args:
            statement: SQL query to execute.
            *multiparams/**params: Bound parameter values to be used in the execution of the query.

        """
        if isinstance(statement, str):
            statement = text(statement)
        return self.connect().execute(statement, *multiparams, **params)

    @contextlib.contextmanager
    def session_scope(self) -> sqlalchemy.orm.session.Session:
        """Provides a transactional scope around a series of operations with rollback in case of failure.

        Bear in mind SQLite and MySQL's storage engine MyISAM do not support rollback transactions,
        so all the modifications performed to the database will persist.

        """
        session = sqlalchemy.orm.session.Session(bind=self._engine, autoflush=False)
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

    @contextlib.contextmanager
    def test_session_scope(self) -> sqlalchemy.orm.session.Session:
        """Provides a transactional scope around a series of operations that will be rolled back at the end.

        Bear in mind SQLite and MySQL's storage engine MyISAM do not support rollback transactions,
        so all the modifications performed to the database will persist.

        """
        # Connect to the database
        connection = self.connect()
        # Begin a non-ORM transaction
        transaction = connection.begin()
        # Bind an individual session to the connection
        session = sqlalchemy.orm.session.Session(bind=connection)
        # If the database supports SAVEPOINT, starting a savepoint will allow to also use rollback
        connection.begin_nested()

        # Define a new transaction event
        @event.listens_for(session, "after_transaction_end")
        def end_savepoint(session, transaction):  # pylint: disable=unused-argument
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
