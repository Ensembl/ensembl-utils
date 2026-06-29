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
"""Unit testing of `ensembl.utils.docs.config` module."""

from contextlib import nullcontext as does_not_raise
from pathlib import Path
from typing import Any, ContextManager
from unittest.mock import MagicMock, patch

import pytest
from pytest import param

from ensembl.utils.docs.config import build_config, configure


@patch.dict("os.environ", {}, clear=True)
def test_build_config_returns_default_sphinx_settings() -> None:
    """Test that `build_config()` returns the shared Sphinx defaults."""
    config = build_config(
        project="example",
        repo_url="https://github.com/Ensembl/example",
        docs_base_url="https://docs.example.org/",
        release="1.2.3",
        include_entrypoints=True,
        html_title="Custom title",
    )
    assert config["project"] == "example"
    assert config["html_title"] == "Custom title"
    assert config["html_theme"] == "pydata_sphinx_theme"
    assert config["myst_enable_extensions"] == ["colon_fence", "substitution"]
    assert "ensembl.utils.docs" in config["extensions"]
    assert "ensembl.utils.docs.entrypoints_ext" in config["extensions"]
    assert config["html_theme_options"]["switcher"] == {
        "json_url": "_static/switcher.json",
        "version_match": "v1.2.3",
    }


@pytest.mark.parametrize(
    ("environment", "release", "json_url", "expected_json_url", "expected_version_match"),
    [
        param({}, None, None, "_static/switcher.json", "dev", id="Local build without release"),
        param({"DOCS_VERSION": "v9.9.9"}, None, None, "_static/switcher.json", "v9.9.9", id="DOCS_VERSION"),
        param({"CI": "true"}, "2.0.0", None, "https://docs.example.org/switcher.json", "v2.0.0", id="CI"),
        param(
            {"CI": "true", "DOCS_VERSION": "v9.9.9"},
            None,
            "https://docs.example.org/custom-switcher.json",
            "https://docs.example.org/custom-switcher.json",
            "v9.9.9",
            id="Explicit json_url",
        ),
    ],
)
def test_build_config_sets_switcher_defaults(
    environment: dict[str, str],
    release: str | None,
    json_url: str | None,
    expected_json_url: str,
    expected_version_match: str,
) -> None:
    """Test that `build_config()` sets version switcher values from arguments and environment.

    Args:
        environment: Environment variables to expose while building the config.
        release: Release argument passed to `build_config()`.
        json_url: Explicit switcher JSON URL passed to `build_config()`, or `None` to use the default.
        expected_json_url: Expected PyData switcher JSON URL.
        expected_version_match: Expected PyData switcher selected version.

    """
    with patch.dict("os.environ", environment, clear=True):
        config = build_config(
            project="example",
            repo_url="https://github.com/Ensembl/example",
            docs_base_url="https://docs.example.org/",
            release=release,
            json_url=json_url,
        )
    assert config["html_theme_options"]["switcher"] == {
        "json_url": expected_json_url,
        "version_match": expected_version_match,
    }


@pytest.mark.parametrize(
    ("coverage_exists", "expectation", "expected_extra_path"),
    [
        param(True, does_not_raise(), True, id="Coverage directory exists"),
        param(False, pytest.warns(UserWarning, match="Coverage root folder"), False, id="Missing coverage"),
    ],
)
def test_build_config_handles_coverage_root(
    tmp_path: Path,
    coverage_exists: bool,
    expectation: ContextManager[Any],
    expected_extra_path: bool,
) -> None:
    """Test that `build_config()` includes existing coverage reports and warns for missing ones.

    Args:
        tmp_path: Fixture that provides a temporary directory path unique to the test invocation.
        coverage_exists: Create the coverage root before building the config.
        expectation: Context manager for the expected warning behaviour.
        expected_extra_path: Whether ``html_extra_path`` should be present in the returned config.

    """
    coverage_root = tmp_path / "reports"
    if coverage_exists:
        coverage_root.mkdir()
    with expectation:
        config = build_config(
            project="example",
            repo_url="https://github.com/Ensembl/example",
            docs_base_url="https://docs.example.org",
            coverage_root=coverage_root,
        )
    assert ("html_extra_path" in config) is expected_extra_path
    if expected_extra_path:
        assert config["html_extra_path"] == [str(coverage_root)]


@pytest.mark.parametrize(
    ("repo_url", "expectation", "expected_icon_links"),
    [
        param(
            "https://github.com/Ensembl/example",
            does_not_raise(),
            [{"name": "GitHub", "url": "https://github.com/Ensembl/example", "icon": "fa-brands fa-github"}],
            id="GitHub repository",
        ),
        param(
            "https://gitlab.com/ensembl/example",
            does_not_raise(),
            [
                {
                    "name": "GitLab",
                    "url": "https://gitlab.com/ensembl/example",
                    "icon": "fa-brands fa-square-gitlab",
                }
            ],
            id="GitLab repository",
        ),
        param(
            "https://example.org/ensembl/example",
            pytest.warns(UserWarning, match="Unrecognised repository platform"),
            [],
            id="Unknown repository platform",
        ),
    ],
)
def test_build_config_sets_repository_icon_links(
    repo_url: str,
    expectation: ContextManager,
    expected_icon_links: list[dict[str, str]],
) -> None:
    """Test that `build_config()` adds repository icon links for supported repository platforms.

    Args:
        repo_url: Repository URL passed to `build_config()`.
        expectation: Context manager for the expected warning behaviour.
        expected_icon_links: Expected icon links in the returned theme options.

    """
    with expectation:
        config = build_config(project="example", repo_url=repo_url, docs_base_url="https://docs.example.org")
    assert config["html_theme_options"]["icon_links"] == expected_icon_links


@pytest.mark.parametrize(
    ("add_pypi_icon", "expected_icon_links"),
    [
        param(
            False,
            [{"name": "GitHub", "url": "https://github.com/Ensembl/example", "icon": "fa-brands fa-github"}],
            id="Do not add PyPI icon",
        ),
        param(
            True,
            [
                {
                    "name": "GitHub",
                    "url": "https://github.com/Ensembl/example",
                    "icon": "fa-brands fa-github",
                },
                {"name": "PyPI", "url": "https://pypi.org/project/example/", "icon": "fa-custom fa-pypi"},
            ],
            id="Add PyPI icon",
        ),
    ],
)
def test_build_config_adds_pypi_icon(add_pypi_icon: bool, expected_icon_links: list[dict[str, str]]) -> None:
    """Test that `build_config()` optionally adds a PyPI icon link.

    Args:
        add_pypi_icon: Whether to add the PyPI icon link.
        expected_icon_links: Expected icon links after removing the repository icon link.

    """
    config = build_config(
        project="example",
        repo_url="https://github.com/Ensembl/example",
        docs_base_url="https://docs.example.org",
        add_pypi_icon=add_pypi_icon,
    )
    assert config["html_theme_options"]["icon_links"] == expected_icon_links


@patch("ensembl.utils.docs.config.build_config", return_value={"project": "example"})
def test_configure_updates_namespace(mock_build_config: MagicMock) -> None:
    """Test that `configure()` injects the generated config into the provided namespace.

    Args:
        mock_build_config: Mocked config builder.

    """
    namespace: dict[str, Any] = {"existing": True}
    configure(
        namespace,
        project="example",
        repo_url="https://github.com/Ensembl/example",
        docs_base_url="https://docs.example.org",
    )
    mock_build_config.assert_called_once_with(
        project="example",
        repo_url="https://github.com/Ensembl/example",
        docs_base_url="https://docs.example.org",
    )
    assert namespace == {"existing": True, "project": "example"}
