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
"""Unit testing of `ensembl.utils.rloader` module."""

import configparser
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest
from pytest import param, raises
import requests.exceptions

from ensembl.utils.rloader import RemoteFileLoader


@dataclass
class MockResponse:
    """Mocks `Response` object returned by `requests.get()` function."""

    text: str
    status_code: int = 200


def mock_requests_get(
    file_path: Path, *args: Any, **kwargs: Any  # pylint: disable=unused-argument
) -> MockResponse:
    """Mocks `requests.get()` function, bypassing the required internet connection."""
    with file_path.open("r") as in_file:
        content = in_file.read()
    return MockResponse(text=content)


class TestRemoteFileLoader:
    """Tests `RemoteFileLoader` class."""

    @pytest.mark.parametrize(
        "file_format, output",
        [
            param("yaml", {"lang": "python", "os": ["linux", "windows"]}, id="YAML file"),
            param("json", {"lang": "python", "os": ["linux", "windows"]}, id="JSON file"),
            param("env", {"DEBUG": "True", "SECRET_KEY": "out_secret"}, id="ENV file"),
            param("txt", "lang: python\nsecret: yes", id="Unknown file format"),
        ],
    )
    @patch("requests.get")
    def test_r_open(self, mock_get: Mock, data_dir: Path, file_format: str, output: Any) -> None:
        """Tests `RemoteFileLoader.r_open()` method for different file formats.

        Args:
            mock_get: Fixture to mock the `requests.get()` function.
            data_dir: Fixture that provides the path to the test data folder matching the test's name.
            file_format: File format to select an ad-hoc parser.
            output: Expected returned output.

        """
        mock_get.side_effect = mock_requests_get
        loader = RemoteFileLoader(file_format)
        content = loader.r_open(data_dir / f"sample.{file_format}")
        assert content == output

    @patch("requests.get")
    def test_r_open_ini_format(self, mock_get: Mock, data_dir: Path) -> None:
        """Tests `RemoteFileLoader.r_open()` method for INI files.

        Args:
            mock_get: Fixture to mock the `requests.get()` function.
            data_dir: Fixture that provides the path to the test data folder matching the test's name.

        """
        mock_get.side_effect = mock_requests_get
        loader = RemoteFileLoader("ini")
        content = loader.r_open(data_dir / "sample.ini")
        parser = configparser.ConfigParser()
        parser["DEFAULT"] = {"DEBUG": "True", "SECRET_KEY": "out_secret"}
        assert content == parser

    @patch("requests.get")
    def test_r_open_status_code(self, mock_get: Mock) -> None:
        """Tests `RemoteFileLoader.r_open()` method when the status code returned is not 200.

        Args:
            mock_get: Fixture to mock the `requests.get()` function.

        """
        mock_get.return_value = MockResponse(text="", status_code=404)
        loader = RemoteFileLoader()
        with raises(requests.exceptions.HTTPError):
            loader.r_open("")

    @pytest.mark.parametrize(
        "exception",
        [
            param(requests.exceptions.HTTPError, id="HTTPError raised"),
            param(requests.exceptions.Timeout, id="Timeout raised"),
        ],
    )
    @patch("requests.get")
    def test_r_open_exceptions(self, mock_get: Mock, exception: Any) -> None:
        """Tests `RemoteFileLoader.r_open()` method when an exception is raised by the URL request.

        Args:
            mock_get: Fixture to mock the `requests.get()` function.
            exception: Expected exception raised.

        """
        mock_get.side_effect = exception
        loader = RemoteFileLoader()
        with raises(exception):
            loader.r_open("")
