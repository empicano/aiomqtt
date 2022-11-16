import sys
from typing import TypeVar

if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias

T = TypeVar("T")

PayloadType: TypeAlias = "str | bytes | bytearray | int | float | None"
