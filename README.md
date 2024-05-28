# Ensembl Python general-purpose utils

[![License](https://img.shields.io/badge/license-Apache_2.0-blue.svg)](https://github.com/Ensembl/ensembl-utils/blob/main/LICENSE)
[![Coverage](https://ensembl.github.io/ensembl-utils/coverage/coverage-badge.svg)](https://ensembl.github.io/ensembl-utils/coverage)
[![CI](https://github.com/Ensembl/ensembl-utils/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Ensembl/ensembl-utils/actions/workflows/ci.yml)

Centralise generic Python utils used by other project within Ensembl design to facilitate frequent tasks such as input file path checks, archive files IO manipulation or logging setup, among others.

For more information, please consult this repository's [GitHub pages](https://ensembl.github.io/ensembl-utils/).

## Getting Started

### Basic installation

This library is publicly available in [pypi.org](https://pypi.org) so it can be easily installed with your favourite Python dependency and packaging management, e.g.
```bash
pip install ensembl-utils
```

### Installing the development environment (with Python `venv`)

If you want to install this library in editable mode, we suggest you to do so via Python's virtual environment module ([venv](https://docs.python.org/3/library/venv.html)):
```bash
python -m venv <VIRTUAL_ENVIRONMENT_NAME>
source <VIRTUAL_ENVIRONMENT_NAME>/bin/activate
git clone https://github.com/Ensembl/ensembl-utils.git
cd ensembl-utils
pip install -e .[cicd,dev,doc]
```
