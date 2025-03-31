# How to contribute

We're very happy about contributions to aiomqtt! 🎉

## Development setup

- Clone the repository
- Install the [uv package manager](https://docs.astral.sh/uv/getting-started/installation/); Then run `./scripts/setup` to install the dependencies and aiomqtt itself
- Run ruff and mypy with `./scripts/check`
- Run the tests with `./scripts/test`

During development, it's often useful to have a local MQTT broker running. You can spin up a local mosquitto broker with Docker via `./scripts/develop`. You can connect to this broker with `aiomqtt.Client("localhost", port=1883)`.

## The documentation

The documentation uses [Sphinx](https://www.sphinx-doc.org/en/master/). You can build it with `./scripts/docs --reload`.

The Markdown source files are located in the `docs` folder. The reference section is mostly generated from the docstrings in the source code. The docstrings are formatted according to the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings).

## Making a pull request

Please check if your changes call for updates to the documentation and don't forget to add your name and contribution to the `CHANGELOG.md`! You can create a draft pull request if your contribution is not yet ready to merge.

### Visual Studio Code

You can find workspace settings and recommended extensions in the `.vscode` folder.
