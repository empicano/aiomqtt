"""Test configuration and utilities."""

import inspect
import os
import pathlib
import secrets
import ssl
import sys

_OS_NAME = sys.platform
_PYTHON_VERSION = ".".join(map(str, sys.version_info[:2]))
_RANDOM_STR = secrets.token_hex(4)

# Tests run faster with a local broker
HOSTNAME = os.environ.get("AIOMQTT_TEST_HOSTNAME", "test.mosquitto.org")
# Choose the CA certificate based on the broker
_SCRIPTS_DIR = pathlib.Path(__file__).parent.parent / "scripts"
_FILENAME = "mosquitto.org.crt" if HOSTNAME == "test.mosquitto.org" else "mosquitto.crt"
SSL_CONTEXT = ssl.create_default_context(cafile=str(_SCRIPTS_DIR / _FILENAME))

USERNAME = "rw"
PASSWORD = b"readwrite"


def unique_topic() -> str:
    """Generate a unique MQTT topic name based on the caller's function name."""
    frame = inspect.currentframe()
    if frame is None or frame.f_back is None:
        msg = "Failed to inspect frame"
        raise RuntimeError(msg)
    func_name = frame.f_back.f_code.co_name
    return f"{_RANDOM_STR}/{_OS_NAME}/{_PYTHON_VERSION}/{func_name}"
