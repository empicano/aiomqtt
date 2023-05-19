# Contributing

We're happy about your contributions to aiomqtt!

## Development setup

- Clone the aiomqtt repository
- Install the Python version noted in `.python-version` via `pyenv`
- [Install poetry](https://python-poetry.org/docs/#installation)
- Install the dependencies with `./scripts/setup`
- You can run black, ruff, and mypy with `./scripts/check --fix`
- You can run the tests with `./scripts/test`

Install [pre-commit](https://pre-commit.com/) so that your code is formatted and checked when you are doing a commit:

```bash
pip install pre-commit
pre-commit install
```

### Visual Studio Code

If you are using VSCode, these are workspace settings and highly recommended extensions to improve the developer experience.

## The documentation

The documentation uses [Sphinx](https://www.sphinx-doc.org/en/master/). The Markdown source files are located in the `docs` folder. You can build the documentation with `./scripts/docs --reload`.

## Committing

After running `git commit`, `pre-commit` will check the committed code. This check can be passed, skipped or failed.

If the check failed, it is possible that `pre-commit` auto-fixed the code, so you only need to re-stage and re-commit. If it did not auto-fix the code, you will need to do so manually.

`pre-commit` will only check the code that is staged, the unstaged code will be stashed during the checks.

## Making a pull request

The branch to contribute to is `main`. You can create a draft pull request if your contribution is not yet ready to merge. Please check if your changes call for updates to the documentation and don't forget to add your name and contribution to the `CHANGELOG.md`!
