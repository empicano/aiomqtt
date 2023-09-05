from __future__ import annotations

import collections.abc
import pathlib
import sys
import typing

import docker  # type: ignore[import]
import pytest


@pytest.fixture
def anyio_backend() -> tuple[str, dict[str, typing.Any]]:
    if sys.platform == "win32":
        from asyncio.windows_events import WindowsSelectorEventLoopPolicy

        return ("asyncio", {"policy": WindowsSelectorEventLoopPolicy()})
    return ("asyncio", {})


@pytest.fixture(scope="session")
def mosquitto() -> collections.abc.Iterator[dict[str, typing.Any]]:
    client = docker.from_env()
    configuration = pathlib.Path(__file__).parent / "mosquitto.conf"
    container = client.containers.run(
        image="eclipse-mosquitto:latest",
        name="mosquitto",
        ports={"1883/tcp": ("127.0.0.1", 1883)},
        volumes=[f"{configuration}:/mosquitto/config/mosquitto.conf"],
        detach=True,
        auto_remove=True,
    )
    yield {"hostname": "localhost", "port": 1883}
    container.stop()
