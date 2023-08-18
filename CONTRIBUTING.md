# Contributing

We're very happy about contributions to aiomqtt! ✨

## Development setup

- Clone the aiomqtt repository
- Install the Python version noted in `.python-version` via `pyenv`
- [Install poetry](https://python-poetry.org/docs/#installation)
- Install the dependencies with `./scripts/setup`
- Run black, ruff, and mypy with `./scripts/check`
- Run the tests with `./scripts/test`
- Spin up a local mosquitto broker via Docker with `./scripts/develop`

## The documentation

The documentation uses [Sphinx](https://www.sphinx-doc.org/en/master/). You can build it with `./scripts/docs --reload`.

The Markdown source files are located in the `docs` folder. The reference section is mostly generated from the docstrings in the source code. The docstrings are formatted according to the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings).

## Making a pull request

The branch to contribute to is `main`. You can create a draft pull request if your contribution is not yet ready to merge. Please check if your changes call for updates to the documentation and don't forget to add your name and contribution to the `CHANGELOG.md`!

### Visual Studio Code

If you're using VSCode, you can find workspace settings and recommended extensions in the `.vscode` folder.
