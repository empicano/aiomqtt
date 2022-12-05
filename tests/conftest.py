from __future__ import annotations

import sys
from typing import Any

import pytest


@pytest.fixture
def anyio_backend() -> tuple[str, dict[str, Any]]:
    if sys.platform == "win32":
        from asyncio.windows_events import WindowsSelectorEventLoopPolicy

        return ("asyncio", {"policy": WindowsSelectorEventLoopPolicy()})
    return ("asyncio", {})
