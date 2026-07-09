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
"""Unit testing of `ensembl.utils.docs.switcher` module."""

from contextlib import nullcontext as does_not_raise
import json
from json import JSONDecodeError
from pathlib import Path
from types import SimpleNamespace
from typing import ContextManager
from unittest.mock import MagicMock, patch

import pytest
from pytest import param

from ensembl.utils.docs.switcher import main


@pytest.mark.parametrize(
    ("initial_content", "expectation"),
    [
        param(
            None,
            does_not_raise(
                [{"name": "v2.0 (latest)", "version": "v2.0", "url": "https://docs.example.org/v2.0/"}]
            ),
            id="Create switcher",
        ),
        param(
            json.dumps(
                [{"name": "v1.0 (latest)", "version": "v1.0", "url": "https://docs.example.org/v1.0/"}]
            ),
            does_not_raise(
                [
                    {"name": "v2.0 (latest)", "version": "v2.0", "url": "https://docs.example.org/v2.0/"},
                    {"name": "v1.0", "version": "v1.0", "url": "https://docs.example.org/v1.0/"},
                ],
            ),
            id="Add latest version",
        ),
        param(
            json.dumps(
                [
                    {"name": "v2.0", "version": "v2.0", "url": "https://docs.example.org/old/v2.0/"},
                    {"name": "v1.0 (latest)", "version": "v1.0", "url": "https://docs.example.org/v1.0/"},
                ]
            ),
            does_not_raise(
                [
                    {"name": "v2.0 (latest)", "version": "v2.0", "url": "https://docs.example.org/v2.0/"},
                    {"name": "v1.0", "version": "v1.0", "url": "https://docs.example.org/v1.0/"},
                ],
            ),
            id="Replace existing version",
        ),
        param("not json", pytest.raises(JSONDecodeError), id="Invalid JSON"),
    ],
)
@patch("ensembl.utils.docs.switcher.argparse.ArgumentParser")
def test_main_updates_switcher_json(
    mock_argument_parser: MagicMock,
    tmp_path: Path,
    initial_content: str | None,
    expectation: ContextManager,
) -> None:
    """Test that `main()` updates the version switcher JSON file.

    Args:
        mock_argument_parser: Mocked command-line parser.
        tmp_path: Fixture that provides a temporary directory path unique to the test invocation.
        initial_content: Existing switcher file content, or `None` to leave it missing.
        expectation: Context manager for the expected exception behaviour.

    """
    switcher_path = tmp_path / "switcher.json"
    if initial_content is not None:
        switcher_path.write_text(initial_content, encoding="utf-8")
    parser = mock_argument_parser.return_value
    parser.parse_args.return_value = SimpleNamespace(
        base_url="https://docs.example.org/",
        version="v2.0",
        switcher=switcher_path,
    )
    with expectation as expected:
        main()
        assert json.loads(switcher_path.read_text(encoding="utf-8")) == expected
    parser.add_argument.assert_any_call(
        "--base-url", required=True, help="Base URL of the documentation site"
    )
    parser.add_argument.assert_any_call("--version", required=True, help="Version to add to the switcher")
    parser.add_argument_src_path.assert_called_once_with("switcher", help="Path to the switcher JSON file")
