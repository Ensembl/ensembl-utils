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
"""Shared Sphinx configuration for Ensembl documentation builds.

Downstream repositories drive their ``docs/conf.py`` from this module::

    from ensembl.utils.docs import configure

    configure(
        globals(),
        project="ensembl-utils",
        repo_url="https://github.com/Ensembl/ensembl-utils",
        docs_base_url="https://ensembl.github.io/ensembl-utils",
    )

Any standard Sphinx setting can be tweaked *after* the ``configure`` call by reassigning or mutating
the matching module-level variable, e.g. ``extensions += ["sphinx_click"]`` or
``html_theme_options["announcement"] = ...``.

"""

__all__ = ["build_config", "configure"]

from datetime import datetime, UTC
import os
from pathlib import Path
from typing import Any
import warnings

from ensembl.utils import StrPath

_STATIC_DIR = Path(__file__).parent / "_static"


def build_config(
    *,
    project: str,
    repo_url: str,
    docs_base_url: str,
    release: str | None = None,
    json_url: str | None = None,
    coverage_root: StrPath | None = None,
    include_entrypoints: bool = False,
    add_pypi_icon: bool = False,
    **overrides: Any,
) -> dict[str, Any]:
    """Return the Ensembl-standard Sphinx configuration as a mapping.

    Args:
        project: Human-readable project name, e.g. ``"ensembl-utils"``.
        repo_url: GitHub or GitLab URL for this repository, used to build the source link.
        docs_base_url: Public base URL where the docs are published; the version switcher JSON is
            expected at ``{docs_base_url}/switcher.json``.
        release: Release version the switcher highlights as current.
        json_url: Location of the switcher JSON. If omitted, hosted/CI builds point at
            ``{docs_base_url}/switcher.json`` and local builds use the relative ``_static/switcher.json``.
        coverage_root: Absolute path to the directory where pytest's HTML coverage report **folder**
            is generated to include it with the documentation.
        include_entrypoints: When ``True``, adds :mod:`ensembl.utils.docs.entrypoints_table` to ``extensions``
            so the CLI entry-points table is auto-injected into the target Markdown file at build time.
        add_pypi_icon: When ``True``, adds the PyPI icon and link to the project at the top right of the page.
        **overrides: Any extra ``conf.py`` values; these win over the defaults.

    Returns:
        A dictionary suitable for injecting into a ``conf.py`` namespace.

    """
    base_url = docs_base_url.rstrip("/")
    # If release version is not provided, take it from the DOCS_VERSION environment variable, which
    # should be set to the git tag name (e.g. "v1.2.0"). Falls back to "dev" for local builds so
    # conf.py is always valid without any environment setup.
    version_match = f"v{release}" if release is not None else os.environ.get("DOCS_VERSION", "dev")
    # If run via GitHub Actions or GitLab CI/CD, point the switcher at the published JSON. Anything
    # else is a local build and uses the copy generated into the build's own _static.
    if json_url is None:
        json_url = f"{base_url}/switcher.json" if os.environ.get("CI") else "_static/switcher.json"
    # Set up Sphinx configuration
    config: dict[str, Any] = {
        # Project information
        "project": project,
        "author": "EMBL-European Bioinformatics Institute",
        "copyright": f"2016-{datetime.now(tz=UTC).year}, EMBL-European Bioinformatics Institute",
        # General configuration
        "extensions": [
            "myst_parser",
            "sphinx.ext.autodoc",
            "sphinx.ext.coverage",
            "sphinx.ext.extlinks",
            "sphinx.ext.intersphinx",
            "sphinx.ext.napoleon",
            "sphinx.ext.viewcode",
            "sphinx_autodoc_typehints",
            "sphinx_copybutton",
            # Registers this package's own setup(app) for deferred config (CSS, ...)
            "ensembl.utils.docs",
        ],
        "language": "en",
        # MyST settings
        "myst_enable_extensions": ["colon_fence", "substitution"],
        "myst_heading_anchors": 3,
        # Autodoc settings
        "autodoc_default_options": {
            "members": True,
            "show-inheritance": True,
            "private-members": False,
            "undoc-members": False,
            "special-members": "__repr__",
        },
        "autodoc_typehints": "description",
        "autodoc_typehints_description_target": "documented",
        "suppress_warnings": ["autodoc.duplicate_object", "sphinx_autodoc_typehints.forward_reference"],
        "typehints_defaults": "comma",
        "typehints_document_rtype_none": False,
        # Napolean settings
        "napoleon_use_ivar": True,
        # Coverage settings
        "coverage_write_headline": False,
        # HTML output settings
        "html_theme": "pydata_sphinx_theme",
        "html_sourcelink_suffix": "",
        "html_last_updated_fmt": "",
        "html_title": project,
        "html_static_path": [],
        "html_css_files": ["ensembl.css"],
        "html_js_files": [
            ("extra-icons.js", {"defer": "defer"}),
        ],
        # Additional HTML options
        "html_theme_options": {
            "footer_start": ["copyright"],
            "footer_center": ["sphinx-version"],
            "header_links_before_dropdown": 4,
            "icon_links": [],
            "logo": {
                "text": project,
            },
            "navbar_align": "left",
            "navbar_center": ["version-switcher", "navbar-nav"],
            "navigation_with_keys": True,
            "search_as_you_type": True,
            "secondary_sidebar_items": {
                "**/*": ["page-toc"],
                "coverage_report": [],
            },
            "show_toc_level": 2,
            "show_version_warning_banner": True,
            "switcher": {
                "json_url": json_url,
                "version_match": version_match,
            },
            "use_edit_page_button": False,
        },
        "html_sidebars": {
            "coverage_report": [],
        },
    }
    if coverage_root:
        if Path(coverage_root).exists():
            config["html_extra_path"] = [str(coverage_root)]
        else:
            warnings.warn(
                f"Coverage root folder '{coverage_root}' does not exist. Remember to run 'make coverage' "
                "before 'make docs'.",
                stacklevel=2,
            )
    if include_entrypoints:
        config["extensions"].append("ensembl.utils.docs.entrypoints_ext")
    if "github" in repo_url:
        config["html_theme_options"]["icon_links"].append(
            {"name": "GitHub", "url": repo_url, "icon": "fa-brands fa-github"}
        )
    elif "gitlab" in repo_url:
        config["html_theme_options"]["icon_links"].append(
            {"name": "GitLab", "url": repo_url, "icon": "fa-brands fa-square-gitlab"}
        )
    else:
        warnings.warn(
            f"Unrecognised repository platform in '{repo_url}'. No icon link will be added.",
            stacklevel=2,
        )
    if add_pypi_icon:
        config["html_theme_options"]["icon_links"].append(
            {
                "name": "PyPI",
                "url": f"https://pypi.org/project/{project}/",
                "icon": "fa-custom fa-pypi",
            }
        )
    config.update(overrides)
    return config


def configure(namespace: dict[str, Any], **kwargs: Any) -> None:
    """Populate a ``conf.py`` namespace in place with the Ensembl defaults.

    Call at the top of ``docs/conf.py`` as ``configure(globals(), ...)``. See :func:`build_config`
    for the accepted keyword arguments.

    Args:
        namespace: The ``conf.py`` module namespace to populate, normally passed as ``globals()``.
        **kwargs: Forwarded verbatim to :func:`build_config`.

    """
    namespace.update(build_config(**kwargs))  # pylint: disable=missing-kwoa
