from typing import Optional, TypeVar, Union

T = TypeVar("T")

PayloadType = Optional[Union[str, bytes, bytearray, int, float]]
