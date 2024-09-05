# Ensembl Python general-purpose utils

[![License](https://img.shields.io/badge/license-Apache_2.0-blue.svg)](https://github.com/Ensembl/ensembl-utils/blob/main/LICENSE)
[![Coverage](https://ensembl.github.io/ensembl-utils/coverage/coverage-badge.svg)](https://ensembl.github.io/ensembl-utils/coverage)
[![CI](https://github.com/Ensembl/ensembl-utils/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Ensembl/ensembl-utils/actions/workflows/ci.yml)
[![Release](https://img.shields.io/pypi/v/ensembl-utils)](https://pypi.org/project/ensembl-utils)

Centralise generic Python utils used by other projects within Ensembl design to facilitate frequent tasks such as input file path checks, archive files IO manipulation or logging setup, among others.

For more information, please consult this repository's [GitHub pages](https://ensembl.github.io/ensembl-utils/).

## Getting Started

### Basic installation

This library is publicly available in [PyPI](https://pypi.org/project/ensembl-utils/) so it can be easily installed with your favourite Python dependency and packaging management tool, e.g.
```bash
pip install ensembl-utils
```

### Quick usage

Besides the standard `import ensembl.utils`, this library also provides some useful command line scripts:
- `extract_file` - to easily extract archive files in different formats

Furthermore, `ensembl-utils` also has a [`pytest`](https://docs.pytest.org/) plugin with some useful functionalities to ease your unit testing. You can enable it by adding it explicitly when running pytest:
```bash
pytest -p ensembl.utils.plugin ...
```

Or adding the following line to your `conftest.py`:
```python
pytest_plugins = ("ensembl.utils.plugin",)
```

## Dependencies

This repository has been developed to support [SQLAlchemy](https://www.sqlalchemy.org) version 1.4 (1.4.45 or later, to ensure "future-compatibility") as well as version 2.0+.
