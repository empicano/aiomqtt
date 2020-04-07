# SPDX-License-Identifier: BSD-3-Clause


class MqttError(Exception):
    """Base exception for all asyncio-mqtt exceptions."""
    pass

class MqttCodeError(MqttError):
    def __init__(self, rc, *args):
        super().__init__(*args)
        self.rc = rc
    
    def __str__(self):
        return f'[code:{self.rc}] {super().__str__()}'
