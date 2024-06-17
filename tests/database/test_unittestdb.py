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

from ensembl.utils.database import UnitTestDB


class TestUnitTestDB:
    """Tests `UnitTestDB` class.

    Attributes:
        dbs: Dictionary of `UnitTestDB` objects with the database name as key.

    """

    dbs: dict[str, UnitTestDB] = {}

    @pytest.mark.dependency(name="test_init", scope="class")
    @pytest.mark.parametrize(
        "src, name, expectation",
        [
            param(Path("mock_db"), None, does_not_raise(), id="Default test database creation"),
            param(Path("mock_db"), "renamed_db", does_not_raise(), id="Rename test database"),
            param(Path("mock_db"), None, does_not_raise(), id="Re-create mock db with absolute path"),
            param(Path("mock_dir"), None, raises(FileNotFoundError), id="Wrong dump folder"),
        ],
    )
    def test_init(
        self,
        request: FixtureRequest,
        data_dir: Path,
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
            db_key = name if name else src.name
            self.dbs[db_key] = UnitTestDB(server_url, src_path, name)
            # Check that the database has been created correctly
            assert self.dbs[db_key], "UnitTestDB should not be empty"
            assert self.dbs[db_key].dbc, "UnitTestDB's database connection should not be empty"
            # Check that the database has been loaded correctly from the dump files
            result = self.dbs[db_key].dbc.execute("SELECT * FROM gibberish")
            assert len(result.fetchall()) == 6, "Unexpected number of rows found in 'gibberish' table"

    @pytest.mark.dependency(depends=["test_init"], scope="class")
    @pytest.mark.parametrize(
        "db_key",
        [
            param("mock_db"),
            param("renamed_db"),
        ],
    )
    def test_drop(self, db_key: str) -> None:
        """Tests the `UnitTestDB.drop()` method.

        Args:
            db_key: Key assigned to the UnitTestDB created in `TestUnitTestDB.test_init()`.

        """
        db_url = self.dbs[db_key].dbc.url
        assert database_exists(db_url)
        self.dbs[db_key].drop()
        assert not database_exists(db_url)
