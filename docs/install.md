# How to install this repository

This Python library only requires Python 3.9+ to work.

## Basic installation

This library is publicly available in [pypi.org](https://pypi.org) so it can be easily installed with your favourite Python dependency and packaging management, e.g.
```bash
pip install ensembl-utils
```

## Development-oriented installation

If you want to install this library in editable mode, we suggest you to do so via Python's virtual environment module ([venv](https://docs.python.org/3/library/venv.html)):
```bash
python -m venv <VIRTUAL_ENVIRONMENT_NAME>
source <VIRTUAL_ENVIRONMENT_NAME>/bin/activate
git clone https://github.com/Ensembl/ensembl-utils.git
cd ensembl-utils
pip install -e .[cicd,docs]
```

Note that the documentation (`docs` tag) is generated using _mkdocs_. For full information visit [mkdocs.org](https://www.mkdocs.org).
