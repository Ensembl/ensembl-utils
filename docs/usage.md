# Using these utils

You can easily take advantage of the provided functionalities by importing this library in your code as usual:
```python
import ensembl.utils
```

This library also provides some scripts that can help you via the command line:
- `extract_file` - to easily extract archive files in different formats

_Note:_ All of them include the `--help` option to provide further information about their purpose and how to use them.

## `pytest` plugin

This repository provides a [`pytest`](https://docs.pytest.org/) plugin with some useful functionalities to do unit testing. In particular, there is one fixture to access the test files in a folder with the same name as the test being run (`data_dir`) and a fixture to build and provide unit test databases (`test_dbs`).

To use these elements you need to enable the plugin once you have installed the repository. There are two main ways to do this:
1. Explicitly indicating it when running `pytest`:
    ```bash
    pytest -p ensembl.utils.plugin ...
    ```

2. Adding the following line to your `conftest.py` file at the root of where the unit tests are located:
    ```python
    pytest_plugins = ("ensembl.utils.plugin",)
    ```

## Dependencies

This repository has been developed to support [SQLAlchemy](https://www.sqlalchemy.org) version 1.4 (1.4.45 or later, to ensure "future-compatibility") as well as version 2.0+.
