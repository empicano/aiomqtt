from __future__ import annotations

import sys
from typing import Any, cast

import pytest

params = [pytest.param(("trio", {}))]
if sys.platform == "win32":
    from asyncio.windows_events import WindowsSelectorEventLoopPolicy

    params.append(
        pytest.param(("asyncio", {"policy": WindowsSelectorEventLoopPolicy()}))
    )
else:
    params.append(pytest.param(("asyncio", {})))


@pytest.fixture(params=params)
def anyio_backend(request: pytest.FixtureRequest) -> tuple[str, dict[str, Any]]:
    return cast(tuple[str, dict[str, Any]], request.param)
