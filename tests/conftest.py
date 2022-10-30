import sys
from typing import Any, Dict, Tuple

import pytest


@pytest.fixture
def anyio_backend() -> Tuple[str, Dict[str, Any]]:
    if sys.platform == "win32":
        from asyncio.windows_events import WindowsSelectorEventLoopPolicy

        return ("asyncio", {"policy": WindowsSelectorEventLoopPolicy()})
    else:
        return ("asyncio", {})
