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
"""Centralised Sphinx configuration and helpers for Ensembl documentation.

This subpackage is intentionally *not* imported by ``ensembl.utils`` itself, so
``import ensembl.utils`` keeps working without the documentation toolchain installed. The Sphinx/theme
dependencies live behind the ``docs`` extra::

    pip install ensembl-utils[docs]
"""

__all__ = ["build_config", "configure", "setup"]

from typing import TYPE_CHECKING, Any

from ensembl.utils.docs.config import _STATIC_DIR, build_config, configure

if TYPE_CHECKING:
    from sphinx.application import Sphinx


def setup(app: "Sphinx") -> dict[str, Any]:
    """Register the app-level configuration with Sphinx.

    Registered automatically because ``"ensembl.utils.docs"`` is added to ``extensions`` by
    :func:`build_config`. This is where things that need the running application go (custom CSS,
    directives, event hooks).

    The package ``_static`` directory (containing ``ensembl.css``) is appended to ``html_static_path``
    on the ``config-inited`` event, *after* the consumption of ``conf.py`` has finished executing. This
    means repos can freely set or extend ``html_static_path`` without clobbering the shared assets,
    and shared assets never clobber repo-local ones, since later entries lose on name collision.

    Args:
        app: The Sphinx application object.

    Returns:
        Sphinx extension metadata.

    """

    def _append_static(app: "Sphinx") -> None:
        static_path: list[str] = app.config.html_static_path
        package_static = str(_STATIC_DIR)
        if package_static not in static_path:
            static_path.append(package_static)
        # Only set logo/favicon if the repo has not already chosen its own
        if not app.config.html_logo:
            app.config.html_logo = str(_STATIC_DIR / "ensembl_mark_white.png")
        if not app.config.html_favicon:
            app.config.html_favicon = str(_STATIC_DIR / "ensembl_favicon.png")

    app.connect("config-inited", lambda app, _config: _append_static(app))
    app.add_css_file("ensembl.css")
    return {"parallel_read_safe": True, "parallel_write_safe": True}
