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
"""Unit testing of `ensembl.utils.checksums` module."""

from pathlib import Path

import pytest
from pytest import param

from ensembl.utils.checksums import get_file_hash, validate_file_hash


@pytest.mark.dependency()
def test_get_file_hash(data_dir: Path) -> None:
    """Tests `get_file_hash()` function.

    Fixtures:
        data_dir
    """
    file_path = data_dir / "file.txt"
    result = get_file_hash(file_path)
    assert result == "0d17ea963a2c325f759fc4066f2fc9b2"


@pytest.mark.dependency(depends=["test_get_file_hash"])
@pytest.mark.parametrize(
    "file_name, hash_value, expected_result",
    [
        param("file.txt", "0d17ea963a2c325f759fc4066f2fc9b2", True, id="Correct hash"),
        param("file.txt", "not_a_hash", False, id="Wrong hash"),
    ],
)
def test_validate_file_hash(data_dir: Path, file_name: str, hash_value: str, expected_result: bool) -> None:
    """Tests `validate_file_hash()` function.

    Fixtures:
        data_dir

    Args:
        file_path: Path to the file to validate.
        hash_value: Expected hash value.
        expected_result: Expected result of the validation.
    """
    file_path = data_dir / file_name
    assert validate_file_hash(file_path, hash_value) == expected_result
