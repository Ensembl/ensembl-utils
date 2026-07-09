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
"""Unit testing of `ensembl.utils.docs` package."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from ensembl.utils import docs
from ensembl.utils.docs.config import _STATIC_DIR


def test_setup_registers_static_assets() -> None:
    """Test that `setup()` registers shared static assets with Sphinx."""
    app = MagicMock()
    metadata = docs.setup(app)
    assert metadata == {"parallel_read_safe": True, "parallel_write_safe": True}
    app.connect.assert_called_once()
    app.add_css_file.assert_called_once_with("ensembl.css")


def test_setup_appends_static_assets_after_config_is_initialised() -> None:
    """Test that the deferred config hook appends shared static assets."""
    app = MagicMock()
    docs.setup(app)
    callback = app.connect.call_args.args[1]
    sphinx_app = SimpleNamespace(
        config=SimpleNamespace(html_static_path=[], html_logo=None, html_favicon=None)
    )
    callback(sphinx_app, sphinx_app.config)
    assert sphinx_app.config.html_static_path == [str(_STATIC_DIR)]
    assert sphinx_app.config.html_logo == str(_STATIC_DIR / "ensembl_mark_white.png")
    assert sphinx_app.config.html_favicon == str(_STATIC_DIR / "ensembl_favicon.png")


def test_setup_preserves_existing_static_assets() -> None:
    """Test that the deferred config hook preserves existing static assets and branding."""
    app = MagicMock()
    docs.setup(app)
    callback = app.connect.call_args.args[1]
    existing_static = str(_STATIC_DIR)
    sphinx_app = SimpleNamespace(
        config=SimpleNamespace(
            html_static_path=[existing_static],
            html_logo="custom-logo.png",
            html_favicon="custom-favicon.ico",
        )
    )
    callback(sphinx_app, sphinx_app.config)
    assert sphinx_app.config.html_static_path == [existing_static]
    assert sphinx_app.config.html_logo == "custom-logo.png"
    assert sphinx_app.config.html_favicon == "custom-favicon.ico"
