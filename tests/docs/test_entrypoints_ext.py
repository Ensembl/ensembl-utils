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
"""Unit testing of `ensembl.utils.docs.entrypoints_ext` module."""

from contextlib import nullcontext as does_not_raise
from pathlib import Path
from types import SimpleNamespace
from typing import ContextManager
from unittest.mock import MagicMock, patch

import pytest
from pytest import param

import ensembl.utils
from ensembl.utils.docs.entrypoints_ext import (
    _SENTINEL_END,
    _SENTINEL_START,
    _build_markdown_table,
    _inject_table,
    _on_builder_inited,
    _read_entry_points,
    setup,
)


@pytest.mark.parametrize(
    ("toml_content", "expectation"),
    [
        param(
            "[project.scripts]\nalpha = 'package.alpha:main'\nbeta = 'package.beta:main'\n",
            does_not_raise({"alpha": "package.alpha:main", "beta": "package.beta:main"}),
            id="Scripts are defined",
        ),
        param("[project]\nname = 'example'\n", does_not_raise({}), id="Scripts are absent"),
        param(None, pytest.raises(FileNotFoundError), id="TOML file is missing"),
    ],
)
def test_read_entry_points(
    tmp_path: Path,
    toml_content: str | None,
    expectation: ContextManager,
) -> None:
    """Test that `_read_entry_points()` reads `project.scripts` from TOML files.

    Args:
        tmp_path: Fixture that provides a temporary directory path unique to the test invocation.
        toml_content: TOML content to write, or `None` to leave the path missing.
        expectation: Context manager for the expected exception behaviour.

    """
    toml_path = tmp_path / "pyproject.toml"
    if toml_content is not None:
        toml_path.write_text(toml_content, encoding="utf-8")
    with expectation as expected:
        assert _read_entry_points(toml_path) == expected


@pytest.mark.parametrize(
    ("entry_points", "expected_table"),
    [
        param({}, "_No entry points are defined in `pyproject.toml`._", id="No entry points"),
        param(
            {"zeta": "package.zeta:main", "alpha": "package.alpha:main"},
            "\n".join(
                [
                    "| Command | Python target      |",
                    "| ------- | ------------------ |",
                    "| `alpha` | `package.alpha:main` |",
                    "| `zeta`  | `package.zeta:main` |",
                ]
            ),
            id="Sorted entry points",
        ),
    ],
)
def test_build_markdown_table(entry_points: dict[str, str], expected_table: str) -> None:
    """Test that `_build_markdown_table()` renders entry points as Markdown.

    Args:
        entry_points: Entry-point mapping to render.
        expected_table: Expected Markdown table.

    """
    assert _build_markdown_table(entry_points) == expected_table


def test_inject_table_replaces_existing_sentinel_region(tmp_path: Path) -> None:
    """Test that `_inject_table()` replaces only the sentinel-delimited region.

    Args:
        tmp_path: Fixture that provides a temporary directory path unique to the test invocation.

    """
    usage_path = tmp_path / "usage.md"
    usage_path.write_text(
        f"# Usage\n\nBefore\n\n{_SENTINEL_START}\nold table\n{_SENTINEL_END}\n\nAfter\n",
        encoding="utf-8",
    )
    _inject_table(usage_path, "new table")
    assert usage_path.read_text(encoding="utf-8") == (
        f"# Usage\n\nBefore\n\n{_SENTINEL_START}\nnew table\n{_SENTINEL_END}\n\nAfter\n"
    )


@patch("ensembl.utils.docs.entrypoints_ext.logger.warning")
def test_inject_table_appends_section_if_sentinels_missing(mock_warning: MagicMock, tmp_path: Path) -> None:
    """Test that `_inject_table()` appends a CLI section when sentinels are missing.

    Args:
        mock_warning: Mocked logger warning method.
        tmp_path: Fixture that provides a temporary directory path unique to the test invocation.

    """
    usage_path = tmp_path / "usage.md"
    usage_path.write_text("# Usage\n", encoding="utf-8")
    _inject_table(usage_path, "new table")
    assert usage_path.read_text(encoding="utf-8") == (
        "# Usage\n\n"
        "## CLI reference\n\n"
        "The following commands are installed as entry points to ease handling common tasks:\n\n"
        f"{_SENTINEL_START}\nnew table\n{_SENTINEL_END}\n"
    )
    mock_warning.assert_called_once()


@pytest.mark.parametrize(
    ("missing_toml", "missing_target"),
    [
        param(False, False, id="Inject table"),
        param(True, False, id="Skip missing TOML"),
        param(False, True, id="Skip missing target"),
    ],
)
@patch("ensembl.utils.docs.entrypoints_ext.logger.warning")
def test_on_builder_inited(
    mock_warning: MagicMock,
    tmp_path: Path,
    missing_toml: bool,
    missing_target: bool,
) -> None:
    """Test that `_on_builder_inited()` injects the table only when inputs exist.

    Args:
        mock_warning: Mocked logger warning method.
        tmp_path: Fixture that provides a temporary directory path unique to the test invocation.
        missing_toml: Leave the configured TOML path missing.
        missing_target: Leave the configured target Markdown path missing.

    """
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    usage_path = docs_dir / "usage.md"
    pyproject_path = tmp_path / "pyproject.toml"
    if not missing_target:
        usage_path.write_text(f"# Usage\n\n{_SENTINEL_START}\n{_SENTINEL_END}\n", encoding="utf-8")
    if not missing_toml:
        pyproject_path.write_text("[project.scripts]\nalpha = 'package.alpha:main'\n", encoding="utf-8")
    app = SimpleNamespace(
        srcdir=str(docs_dir),
        config=SimpleNamespace(entrypoints_target_file="usage.md", entrypoints_toml_file="../pyproject.toml"),
    )
    _on_builder_inited(app)  # type: ignore[arg-type]
    if missing_toml or missing_target:
        mock_warning.assert_called_once()
    else:
        mock_warning.assert_not_called()
        assert "`alpha`" in usage_path.read_text(encoding="utf-8")


def test_setup_registers_sphinx_extension() -> None:
    """Test that `setup()` registers config values and the builder event."""
    app = MagicMock()
    metadata = setup(app)
    assert metadata == {
        "version": ensembl.utils.__version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
    app.add_config_value.assert_any_call("entrypoints_target_file", "user_guide/usage.md", "env")
    app.add_config_value.assert_any_call("entrypoints_toml_file", "../pyproject.toml", "env")
    app.connect.assert_called_once_with("builder-inited", _on_builder_inited)
