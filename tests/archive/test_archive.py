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
import io
from pathlib import Path
import shutil
import sys
import tarfile

import pytest
from pytest import param

from ensembl.utils.archive import open_gz_file, extract_file


@pytest.mark.dependency(name="open_gz_file_read")
@pytest.mark.parametrize(
    "src_file, expected_file",
    [
        param("sample.txt.gz", "sample.txt", id="gzip file"),
        param("sample.txt", "sample.txt", id="uncompressed file"),
    ],
)
def test_open_gz_file_read(data_dir: Path, src_file: str, expected_file: str) -> None:
    """Tests `open_gz_file()` function for read mode.

    Args:
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


@pytest.mark.dependency(depends=["open_gz_file_read"])
@pytest.mark.parametrize(
    "file_name",
    [
        param("test.txt.gz", id="gzip file"),
        param("test.txt", id="uncompressed file"),
    ],
)
def test_open_gz_file_write(tmp_path: Path, file_name: str) -> None:
    """Tests `open_gz_file()` function for write mode.

    Args:
        tmp_path: Fixture that provides a temporary directory path unique to the test invocation.
        file_name: Name of the file to be created and written to.

    """
    text = "test content\n"
    file_path = tmp_path / file_name
    with open_gz_file(file_path, mode="wt") as out_file:
        out_file.write(text)
    # Check if the content has been written correctly
    with open_gz_file(file_path) as in_file:
        assert text == "".join(in_file.readlines())


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


@pytest.mark.parametrize("archive_format", ["zip", "tar", "gztar", "bztar", "xztar"])
def test_extract_generated_archive(tmp_path: Path, archive_format: str) -> None:
    """Extract supported archives into a newly created destination directory."""
    source = tmp_path / "source"
    source.mkdir()
    (source / "sample.txt").write_text("archive contents\n")
    archive = shutil.make_archive(str(tmp_path / "sample"), archive_format, source)
    destination = tmp_path / "extracted"

    extract_file(archive, destination)

    assert (destination / "sample.txt").read_text() == "archive contents\n"


@pytest.mark.skipif(sys.version_info < (3, 12), reason="Explicit extraction filters require Python 3.12")
def test_extract_tar_rejects_parent_path(tmp_path: Path) -> None:
    """Retain the data filter when extracting tar archives."""
    archive = tmp_path / "unsafe.tar"
    member = tarfile.TarInfo("../outside.txt")
    member.size = 1
    with tarfile.open(archive, "w") as tar:
        tar.addfile(member, io.BytesIO(b"x"))

    with pytest.raises(tarfile.OutsideDestinationError):
        extract_file(archive, tmp_path / "extracted")

    assert not (tmp_path / "outside.txt").exists()
