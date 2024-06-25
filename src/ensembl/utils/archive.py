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
"""Utils for common IO operations over archive files, e.g. tar or gzip."""

from __future__ import annotations

__all__ = [
    "SUPPORTED_ARCHIVE_FORMATS",
    "open_gz_file",
    "extract_file",
]

from contextlib import contextmanager
import gzip
from pathlib import Path
import shutil
from typing import Generator, TextIO

from ensembl.utils import StrPath
from ensembl.utils.argparse import ArgumentParser


def _unpack_gz_files(src_file: StrPath, dst_dir: StrPath) -> None:
    """Unpacks `src_file` to `dst_dir`.

    Args:
        src_file: File path to unpack (with ".gz" extension).
        dst_dir: Directory path to unpack the file into.

    """
    # Remove '.gz' extension to create the destination file name
    dst_file = Path(dst_dir) / Path(src_file).stem
    with gzip.open(src_file, "rb") as f_in:
        with dst_file.open("wb") as f_out:
            shutil.copyfileobj(f_in, f_out)


shutil.register_unpack_format("gzip", [".gz"], _unpack_gz_files, description="GZIP file")

# Each registered format is a tuple (name, extensions, description)
SUPPORTED_ARCHIVE_FORMATS = [ext for elem in shutil.get_unpack_formats() for ext in elem[1]]


@contextmanager
def open_gz_file(file_path: StrPath) -> Generator[TextIO, None, None]:
    """Yields an open file object, even if the file is compressed with gzip.

    The file is expected to contain a text, and this can be used with the usual "with".

    Args:
        file_path: A (single) file path to open.

    """
    src_file = Path(file_path)
    if src_file.suffix == ".gz":
        with gzip.open(src_file, "rt") as fh:
            yield fh
    else:
        with src_file.open("rt") as fh:
            yield fh


def extract_file(src_file: StrPath, dst_dir: StrPath) -> None:
    """Extracts the `src_file` into `dst_dir`.

    If the file is not an archive, it will be copied to `dst_dir`. `dst_dir` will be created if it
    does not exist.

    Args:
        src_file: Path to the file to unpack.
        dst_dir: Path to the folder where to extract the file.

    """
    src_file = Path(src_file)
    extensions = {"".join(src_file.suffixes[i:]) for i in range(0, len(src_file.suffixes))}

    if extensions.intersection(SUPPORTED_ARCHIVE_FORMATS):
        shutil.unpack_archive(src_file, dst_dir)
    else:
        # Replicate the functionality of shutil.unpack_archive() by creating `dst_dir`
        Path(dst_dir).mkdir(parents=True, exist_ok=True)
        shutil.copy(src_file, dst_dir)


def extract_file_cli() -> None:
    """Entry-point for the `extract_file` method"""
    parser = ArgumentParser(description="Extracts file to the given location.")
    parser.add_argument_src_path("--src_file", required=True, help="Path to the file to unpack")
    parser.add_argument_dst_path(
        "--dst_dir", default=Path.cwd(), help="Path to the folder where to extract the file"
    )
    args = parser.parse_args()
    extract_file(args.src_file, args.dst_dir)
