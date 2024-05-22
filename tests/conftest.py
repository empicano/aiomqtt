from __future__ import annotations

import sys
from typing import Any

import pytest


# No longer needed, this also works with Trio
@pytest.fixture
def anyio_backend() -> tuple[str, dict[str, Any]]:
    return ("trio", {})
