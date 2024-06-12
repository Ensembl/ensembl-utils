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
"""Allow to seamlessly load / read the content of a remote file as if it was located locally."""

from __future__ import annotations

__all__ = ["RemoteFileLoader"]

import configparser
import json
import logging
from io import StringIO
from typing import Optional, Any

import dotenv
import requests
import requests.exceptions
import yaml


logger = logging.getLogger(__name__)


class RemoteFileLoader:
    """Loads remote files, allowing specific format parsing options.

    Args:
        parser: Parser to use for this object. Default: `None` (no format-specific parsing done).

    Attributes:
        available_formats: File formats with ad-hoc parsers available.
        parser: Parser selected for this object.

    """

    available_formats: set[str] = {"yaml", "ini", "env", "json"}
    parser: Optional[str] = None

    def __init__(self, parser: Optional[str] = None) -> None:
        if parser in self.available_formats:
            self.parser = parser

    def __parse(self, content: str) -> Any:
        if self.parser == "yaml":
            return yaml.load(content, yaml.SafeLoader)
        if self.parser == "ini":
            config = configparser.ConfigParser()
            try:
                config.read_string(content)
            except configparser.MissingSectionHeaderError:
                content = "[DEFAULT]\n" + content
                config.read_string(content)
            return config
        if self.parser == "env":
            return dotenv.dotenv_values(stream=StringIO(content))
        if self.parser == "json":
            return json.loads(content)
        # Only return content, no parsing
        return content

    def r_open(self, url: str) -> Any:
        """Returns the parsed remote file from the given URL.

        Args:
            url: URL of the remote file to fetch.

        Raises:
            requests.exception.HTTPError: If loading or requesting the given URL returned an error.
            requests.exception.Timeout: If a timeout was raised whilst requesting the given URL.

        """
        try:
            r = requests.get(url, timeout=120)
            if r.status_code == 200:
                return self.__parse(r.text)
            raise requests.exceptions.HTTPError(response=r)
        except requests.exceptions.HTTPError as ex:
            logger.exception(f"Error with request to {url}: {ex}")
            raise ex
        except requests.exceptions.Timeout as ex:
            logger.exception(f"Request timed out {url}: {ex}")
            raise ex
