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
"""Unit testing of `ensembl.utils.archive` module."""

import filecmp
from pathlib import Path

import pytest
from pytest import param

from ensembl.utils.archive import open_gz_file, extract_file


@pytest.mark.parametrize(
    "src_file, expected_file",
    [
        param("sample.txt.gz", "sample.txt", id="gzip file"),
        param("sample.txt", "sample.txt", id="uncompressed file"),
    ],
)
def test_open_gz_file(data_dir: Path, src_file: str, expected_file: str) -> None:
    """Tests `open_gz_file()` function.

    Args:
        tmp_path: Fixture that provides a temporary directory path unique to the test invocation.
        data_dir: Fixture that provides the path to the test data folder matching the test's name.
        src_file: Source file to open.
        expected_file: File with the expected content to be found in the source file.

    """
    # Get content of archive file
    with open_gz_file(data_dir / src_file) as in_file:
        src_content = in_file.readlines()
    # Get expected content
    expected_path = data_dir / expected_file
    with expected_path.open("r") as in_file:
        expected_content = in_file.readlines()
    assert src_content == expected_content


@pytest.mark.parametrize(
    "src_file, expected_output",
    [
        param("sample.tar", "sample.txt", id="tar file"),
        param("sample.txt.gz", "sample.txt", id="gzip file"),
        param("sample.txt", "sample.txt", id="uncompressed file"),
    ],
)
def test_extract_file(tmp_path: Path, data_dir: Path, src_file: str, expected_output: str) -> None:
    """Tests `extract_file()` function.

    Args:
        tmp_path: Fixture that provides a temporary directory path unique to the test invocation.
        data_dir: Fixture that provides the path to the test data folder matching the test's name.
        src_file: Source file to extract.
        expected_output: File with the expected content after extracting the source file.

    """
    extract_file(data_dir / src_file, tmp_path)
    assert filecmp.cmp(tmp_path / expected_output, data_dir / expected_output)
