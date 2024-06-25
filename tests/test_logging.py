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
"""Unit testing of `ensembl.utils.logging` module."""

import argparse
import logging
from pathlib import Path

import pytest
from pytest import param

from ensembl.utils.logging import LogLevel, init_logging, init_logging_with_args


@pytest.mark.parametrize(
    "log_level, log_file",
    [
        param(logging.WARNING, "", id="No log file"),
        param(logging.ERROR, "app.log", id="Add log file"),
    ],
)
def test_init_logging(tmp_path: Path, log_level: LogLevel, log_file: str) -> None:
    """Tests `init_logging()` function.

    Args:
        tmp_path: Fixture that provides a temporary directory path unique to the test invocation.
        log_level: Minimum logging level.
        log_file: Logging file where to write logging messages besides the standard error.

    """
    if log_file:
        num_handlers = 2
        init_logging(log_level=log_level, log_file=tmp_path / log_file, log_file_level=log_level)
    else:
        num_handlers = 1
        init_logging(log_level=log_level)
    assert len(logging.root.handlers) == num_handlers
    for handler in logging.root.handlers:
        assert handler.level == log_level


def test_init_logging_with_args() -> None:
    """Tests `init_logging_with_args()` function."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--log_level")
    args = parser.parse_args(["--log_level", "DEBUG"])
    init_logging_with_args(args)
    assert len(logging.root.handlers) == 1
    # NOTE: from 3.11 the log_level difference can be changed to: logging.getLevelNamesMapping().keys()
    assert logging.root.handlers[0].level == logging.DEBUG
