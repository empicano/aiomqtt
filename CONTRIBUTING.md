# How to contribute

We're happy about contributions to aiomqtt! 🎉

## Development setup

- Clone the repository
- Install the [uv package manager](https://docs.astral.sh/uv/getting-started/installation/)
- Run ruff and mypy with `./scripts/check`
- Run the tests with `./scripts/test`

> [!TIP]
> During development, it's often useful to have a local MQTT broker running. You can spin up a local mosquitto broker via Docker with `./scripts/mosquitto`. Connect to this broker with `aiomqtt.Client("localhost")`. Run `AIOMQTT_TEST_HOSTNAME=localhost ./scripts/test` to run the tests against the local broker instead of the public `test.mosquitto.org` broker.

## The documentation

The documentation lives in the `docs` folder. Examples should be self-contained and runnable as-is.

## Making a pull request

Please check if your changes call for updates to the documentation and don't forget to add your name and contribution to the `CHANGELOG.md`! You can create a draft PR if your contribution is not yet ready to merge.

## Release

1. Adjust the version in `pyproject.toml`
1. Update the `CHANGELOG.md`
1. Create a new release on GitHub.
