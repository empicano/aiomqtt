"""Test configuration and utilities."""

import inspect
import secrets
import sys

_OS_NAME = sys.platform
_PYTHON_VERSION = ".".join(map(str, sys.version_info[:2]))
_RANDOM_STR = secrets.token_hex(4)


def unique_topic() -> str:
    """Generate a unique MQTT topic name based on the caller's function name."""
    frame = inspect.currentframe()
    if frame is None or frame.f_back is None:
        msg = "Failed to inspect frame"
        raise RuntimeError(msg)
    func_name = frame.f_back.f_code.co_name
    return f"{_RANDOM_STR}/{_OS_NAME}/{_PYTHON_VERSION}/{func_name}"
