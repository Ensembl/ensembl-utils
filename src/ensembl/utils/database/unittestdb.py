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
"""Unit testing database handler.

This module provides the main class to create and drop testing databases, populating them from
preexisting dumps (if supplied).

Examples:

    >>> from ensembl.utils.database import UnitTestDB
    >>> # For more safety use the context manager (automatically drops the database even if things go wrong):
    >>> with UnitTestDB("mysql://user:passwd@mysql-server:4242/", "path/to/dumps", "my_db") as test_db:
    >>>    dbc = test_db.dbc

    >>> # If you know what you are doing you can also control when the test_db is dropped:
    >>> test_db = UnitTestDB("mysql://user:passwd@mysql-server:4242/", "path/to/dumps", "my_db")
    >>> # You can access the database via test_db.dbc, for instance:
    >>> dbc = test_db.dbc
    >>> # At the end do not forget to drop the database
    >>> test_db.drop()

"""

from __future__ import annotations

__all__ = [
    "UnitTestDB",
]

import os
from pathlib import Path
import subprocess
from typing import Any

import sqlalchemy
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.schema import MetaData
from sqlalchemy_utils.functions import create_database, database_exists, drop_database

from ensembl.utils import StrPath
from ensembl.utils.database.dbconnection import DBConnection, StrURL


TEST_USERNAME = os.environ.get("USER", "pytestuser")


class UnitTestDB:
    """Creates and connects to a new test database, applying the schema and importing the data.

    Args:
        server_url: URL of the server hosting the database.
        metadata: Use this metadata to create the schema instead of using an SQL schema file.
        dump_dir: Directory path with the database schema in `table.sql` (mandatory) and one TSV data
            file (without headers) per table following the convention `<table_name>.txt` (optional).
        name: Name to give to the new database. If not provided, the last directory name of `dump_dir`
            will be used instead. In either case, the new database name will be prefixed by the username.
        tmp_path: Temp dir where the test db is created if using SQLite (otherwise use current dir).

    Attributes:
        dbc: Database connection handler.

    Raises:
        FileNotFoundError: If `table.sql` is not found.

    """

    def __init__(
        self,
        server_url: StrURL,
        dump_dir: StrPath | None = None,
        name: str | None = None,
        metadata: MetaData | None = None,
        tmp_path: StrPath | None = None,
    ) -> None:
        db_url = make_url(server_url)
        if not name:
            name = Path(dump_dir).name if dump_dir else "testdb"
        db_name = f"{TEST_USERNAME}_{name}"

        # Add the database name to the URL
        if db_url.get_dialect().name == "sqlite":
            db_path = Path(tmp_path) / db_name if tmp_path else db_name
            db_url = db_url.set(database=f"{db_path}.db")
        else:
            db_url = db_url.set(database=db_name)
        # Enable "local_infile" variable for MySQL databases to allow importing data from files
        connect_args = {}
        if db_url.get_dialect().name == "mysql":
            connect_args["local_infile"] = 1
        # Create the database, dropping it beforehand if it already exists
        if database_exists(db_url):
            drop_database(db_url)
        create_database(db_url)
        # Establish the connection to the database, load the schema and import the data
        try:
            self.dbc = DBConnection(db_url, connect_args=connect_args, reflect=False)
            self._load_schema_and_data(dump_dir, metadata)
        except:
            # Make sure the database is deleted before raising the exception
            drop_database(db_url)
            raise
        # Update the loaded metadata information of the database
        self.dbc.load_metadata()

    def _load_schema_and_data(
        self, dump_dir: StrPath | None = None, metadata: MetaData | None = None
    ) -> None:
        with self.dbc.begin() as conn:
            # Set InnoDB engine as default and disable foreign key checks for MySQL databases
            if self.dbc.dialect == "mysql":
                conn.execute(text("SET default_storage_engine=InnoDB"))
                conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))

            # Load the schema
            if metadata:
                metadata.create_all(conn)
            elif dump_dir:
                with Path(dump_dir, "table.sql").open("r") as schema:
                    for query in "".join(schema.readlines()).split(";"):
                        if query.strip():
                            conn.execute(text(query))

            # And import any available data for each table
            if dump_dir:
                for tsv_file in Path(dump_dir).glob("*.txt"):
                    table = tsv_file.stem
                    self._load_data(conn, table, tsv_file)

            # Re-enable foreign key checks for MySQL databases
            if self.dbc.dialect == "mysql":
                conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))

    def __repr__(self) -> str:
        """Returns a string representation of this object."""
        return f"{self.__class__.__name__}({self.dbc.url!r})"

    def drop(self) -> None:
        """Drops the database."""
        drop_database(self.dbc.url)
        # Ensure the connection pool is properly closed and disposed
        self.dbc.dispose()

    def _load_data(self, conn: sqlalchemy.engine.Connection, table: str, src: StrPath) -> None:
        """Loads the table data from the given file.

        Args:
            conn: Open connection to the database.
            table: Table name to load the data to.
            src: File path with the data in TSV format (without headers).

        """
        if self.dbc.dialect == "sqlite":
            # SQLite does not have an equivalent to "LOAD DATA": use its ".import" command instead
            subprocess.run(["sqlite3", self.dbc.db_name, ".mode tabs", f".import {src} {table}"], check=True)
        elif self.dbc.dialect == "postgresql":
            conn.execute(text(f"COPY {table} FROM '{src}'"))
        elif self.dbc.dialect == "sqlserver":
            conn.execute(text(f"BULK INSERT {table} FROM '{src}'"))
        else:
            conn.execute(text(f"LOAD DATA LOCAL INFILE '{src}' INTO TABLE {table}"))

    def __enter__(self) -> UnitTestDB:
        return self

    def __exit__(self, *args: Any) -> None:
        self.drop()
