# Contributing

We're very happy about contributions to aiomqtt!

## Development setup

- Clone the aiomqtt repository
- Install the Python version noted in `.python-version` via `pyenv`
- [Install poetry](https://python-poetry.org/docs/#installation)
- Install the dependencies with `./scripts/setup`
- Run black, ruff, and mypy with `./scripts/check`
- Run the tests with `./scripts/test`

## The documentation

The documentation uses [Sphinx](https://www.sphinx-doc.org/en/master/). The Markdown source files are located in the `docs` folder. You can build the documentation with `./scripts/docs --reload`.

## Making a pull request

The branch to contribute to is `main`. You can create a draft pull request if your contribution is not yet ready to merge. Please check if your changes call for updates to the documentation and don't forget to add your name and contribution to the `CHANGELOG.md`!

### Visual Studio Code

If you're using VSCode, you can find workspace settings and recommended extensions in the `.vscode` folder.
