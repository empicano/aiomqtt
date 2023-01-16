# Contributing

Hi there! Thanks for your interest in contributing to _asyncio-mqtt_.

## Setting up an environment

Clone the `asyncio-mqtt` repository.

Inside the repository, create a virtual environment:

```bash
python3 -m venv .venv
```

Activate the virtual environment:

```bash
source .venv/bin/activate
```

Upgrade `pip`:

```bash
pip install --upgrade pip
```

Install the development dependencies:

```bash
pip install -e .[tests,lint,format,docs]
```

Install [pre-commit](https://pre-commit.com/) so that your code is formatted and checked when you are doing a commit:

```bash
pip install pre-commit
pre-commit install
```

### Visual Studio Code

If you are using VSCode, these are workspace settings and highly recommended extensions to improve developer experience.

## Testing

To test the code use [pytest](https://docs.pytest.org/en/7.1.x/):

```bash
pytest
```

To get the full test coverage report of `asyncio-mqtt`, run the following command:

```bash
pytest --cov=src --cov=tests --cov-report=html
```

You can see the coverage report in `htmlcov/index.html`.

## Building the documentation

The documentation uses [Sphinx](https://www.sphinx-doc.org/en/master/). The source files are located in the `docs` folder. You can build it by running `./scripts/docs` or `./scripts/docs --no-reload` if you don't want to have the documentation rebuilt automatically when you change a file.

## Committing

After running `git commit`, `pre-commit` will check the committed code. This check can be passed, skipped or failed.

If the check failed, it is possible that `pre-commit` auto-fixed the code, so you only need to re-stage and re-commit. If it did not auto-fix the code, you will need to do so manually.

`pre-commit` will only check the code that is staged, the unstaged code will be stashed during the checks.

## Making a Pull Request

The branch to contribute is `main`. You can create a draft pull request as long as your contribution is not ready. Please also update the `CHANGELOG.md` with the changes that your pull request makes!
