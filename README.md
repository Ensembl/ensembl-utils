# Ensembl Python general-purpose utils

[![GitHub license](https://img.shields.io/github/license/Ensembl/ensembl-utils)](https://github.com/Ensembl/ensembl-utils/blob/main/LICENSE)

Centralise generic Python utils used by other project within Ensembl design to facilitate frequent tasks such as input file path checks, archive files IO manipulation or logging setup, among others.

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
