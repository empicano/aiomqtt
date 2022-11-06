# SPDX-License-Identifier: BSD-3-Clause
from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("asyncio-mqtt")
except PackageNotFoundError:
    pass
