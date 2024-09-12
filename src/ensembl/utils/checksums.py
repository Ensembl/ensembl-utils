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
"""Utils for common hash operations (often referred to as checksums) over files, e.g. MD5 or SHA128."""

import hashlib
from pathlib import Path

from ensembl.utils import StrPath


def get_file_hash(file_path: StrPath, algorithm: str = "md5") -> str:
    """Returns the hash value for a given file and hash algorithm.

    Args:
        file_path: File path to get the hash for.
        algorithm: Secure hash or message digest algorithm name.
    """
    hash_func = hashlib.new(algorithm)
    with Path(file_path).open("rb") as f:
        data_bytes = f.read()
    hash_func.update(data_bytes)
    return hash_func.hexdigest()


def validate_file_hash(file_path: StrPath, hash_value: str, algorithm: str = "md5") -> bool:
    """Returns true if the file's hash value is the same as the one provided for that hash
    algorithm, false otherwise.

    Args:
        file_path: Path to the file to validate.
        hash_value: Expected hash value.
        algorithm: Secure hash or message digest algorithm name.
    """
    file_hash = get_file_hash(file_path, algorithm)
    return file_hash == hash_value
