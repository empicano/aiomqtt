# Contributing

## Setting up an environment

Clone the `asyncio-mqtt`.

Inside the repository, create a virtual environment.

```bash
python3 -m venv env
```

Activate the virtual environment.

```bash
source ./env/bin/activate
```

Upgrade `pip`.

```bash
pip install --upgrade pip
```

Install the development dependencies.

```bash
pip install -e .[tests,lint,format]
```

Install [pre-commit](https://pre-commit.com/) so that your code is formatted and checked when you are doing a commit.

```bash
pip install pre-commit
pre-commit install
```

### Visual Studio Code

If you are using VSCode, here are the settings to activate on save,

- `black` and `isort` to format.
- `mypy` to lint.
- Install [charliermarsh.ruff](https://marketplace.visualstudio.com/items?itemName=charliermarsh.ruff) extension to lint (`ruff` is a fast equivalent to `flake8`)

```json
{
  "[python]": {
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  },
  "python.formatting.provider": "black",
  "python.linting.mypyEnabled": true
}
```

## Testing

To test the code use [pytest](https://docs.pytest.org/en/7.1.x/).

```bash
pytest
```

To do the full coverage of `asyncio-mqtt`, run the following command.

```bash
pytest --cov=src --cov=tests --cov-report=html
```

To view the coverage open `htmlcov/index.html`.

## Committing

After doing `git commit`, `pre-commit` will check the committed code.
The check can be passed, skipped or failed.
If the check failed, it is possible it auto-fixed the code, so you will only need to stage and commit again for it to pass.
If it did not auto-fixed the code, you will need to do it manually.
`pre-commit` will only check the code that is staged, the unstaged code will be stashed during the checks.

## Making a Pull Request

The branch to contribute is `master`.
You should create a draft pull request if you still need to work on it.
You should update `CHANGELOG.md` to reflect the change done in your pull request.
