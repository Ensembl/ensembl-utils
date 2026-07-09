# Using these utils

You can easily take advantage of the provided functionalities by importing this library in your code as usual:

```python
import ensembl.utils
```

This library also provides some scripts to facilitate integrating these tasks into your workflow. To get the full list, please refer to the `[project.scripts]` section in the `pyproject.toml` file. All scripts include the `--help` option, which provides further information about their purpose and usage.

## Pytest plugin

This repository provides a [`pytest`](https://docs.pytest.org/) plugin with fixtures and command-line options for common Ensembl testing workflows.

To use these elements you need to enable the plugin once you have installed the repository. There are two main ways to do this:

1. Explicitly indicating it when running `pytest`:

    ```bash
    pytest -p ensembl.utils.plugin ...
    ```

2. Adding the following line to your `conftest.py` file at the root of where the unit tests are located:

    ```python
    pytest_plugins = ("ensembl.utils.plugin",)
    ```

The plugin provides the following fixtures:

| Fixture        | Purpose |
| -------------- | ------- |
| `data_dir`     | Returns the test data directory matching the test module name. |
| `assert_files` | Compares two text files and reports a unified diff when they differ. |
| `db_factory`   | Creates `UnitTestDB` instances on demand within a test module. |
| `test_dbs`     | Creates one or more test databases via indirect parametrization. |

It also adds these pytest options:

| Option       | Purpose |
| ------------ | ------- |
| `--server`   | Sets the SQLAlchemy database URL used to create test databases. Defaults to `DB_HOST` or `sqlite:///`. |
| `--keep-dbs` | Keeps generated test databases after the test run for inspection. |

## Sphinx documentation

The `ensembl.utils.docs` module provides the shared Sphinx + PyData configuration used by Ensembl Python repositories. Downstream projects can import it from their own `docs/conf.py` to reuse the Ensembl theme, MyST Markdown support, autodoc defaults, source links, version switcher, and shared static assets.

First, make sure the repository installs `ensembl-utils` with its documentation dependencies. For an editable checkout, the install command usually looks like this:

```bash
pip install -e .[docs]
```

Then create or update `docs/conf.py` in the downstream repository:

```python
from pathlib import Path

import my_package
from ensembl.utils.docs import configure


coverage_root = Path(__file__).parent / "reports"
configure(
    globals(),
    project="my-package",
    repo="Ensembl/my-package",
    release=my_package.__version__,
    docs_base_url="https://ensembl.github.io/my-package",
    coverage_root=coverage_root if coverage_root.exists() else None,
)
```

The `coverage_root` argument is optional. Use it when the repository generates an HTML coverage report that should be included in the documentation build. It must point to the coverage report's root directory, i.e. if you generate the report in `docs/reports/htmlcov`, `coverage_root` needs to point to `docs/reports` (relative or absolute path). Note that the directory needs to exist before Sphinx runs. If the project keeps coverage tools in a separate optional dependency group, install that group as well, then generate coverage before building the docs:

```bash
pip install -e .[cicd,docs]
make coverage && make docs
```

Project-specific Sphinx and PyData settings can be changed after calling `configure()`. For example, append extra extensions or update `html_theme_options` in the same `conf.py` file.

To include API reference pages in the build, generate them before running Sphinx. A typical `Makefile` target is:

```makefile
apidoc:
	sphinx-apidoc -o docs/reference/ src/my_package --force --module-first --no-toc --implicit-namespaces

docs: apidoc
	sphinx-build -b html docs/ docs/_build/html
```

If the downstream package defines command-line scripts in `[project.scripts]`, `configure()` can also enable an automatically maintained entry-point table:

```python
configure(
    globals(),
    project="my-package",
    repo="Ensembl/my-package",
    release=my_package.__version__,
    docs_base_url="https://ensembl.github.io/my-package",
    include_entrypoints=True,
)
```

By default, the table is written into `docs/user_guide/usage.md`, between the entry-point table start and end comments. To use a different page or `pyproject.toml` location, set these values after `configure()`:

```python
entrypoints_target_file = "user_guide/usage.md"
entrypoints_toml_file = "../pyproject.toml"
```

Check the section [Building the documentation locally](documentation.md) to learn more about how to build and preview your documentation before pushing your changes.

## CLI reference

The following commands are installed as entry points to ease handling common tasks:

<!-- entrypoints-table:start -->
<!-- entrypoints-table:end -->

All scripts support `--help` for usage details. All but `update_docs_switcher` support `--version` to return the library's version.
