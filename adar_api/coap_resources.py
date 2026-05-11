"""CoAP resource URIs for the ADAR API.

This module defines the CoAP resource paths for communicating with ADAR devices.

Versioning:
    Resources are versioned (v0, v1, etc.) to allow protocol evolution while
    maintaining backwards compatibility.

    - **v0**: No authentication, no CRC.
    - **v1**: All endpoints bumped, login/logout/reboot added, CRC mandatory.

Usage:
    The Adar class uses RESOURCE_PATHS internally to resolve paths based on the
    detected protocol version. The individual constants below are kept for
    backwards compatibility with external scripts.
"""

# Individual constants kept for backwards compatibility with external scripts.
# v0 resources
DEVICE_INFO_V0 = "/device_info/v0"
STATE_V0 = "/state/v0"
STATUS_V0 = "/status/v0"
NETWORK_CONFIG_V0 = "/network_config/v0"
FACTORY_RESET_V0 = "/factory_reset/v0"
ERRORS_V0 = "/errors/v0"
OBSERVERS_V0 = "/observers/v0"
POINTCLOUD_V0 = "/pointcloud/v0"
TRANSMISSION_CODE_V0 = "/transmission_code/v0"

# v1 resources
DEVICE_INFO = "/device_info/v1"
STATE = "/state/v1"
STATUS = "/status/v1"
NETWORK_CONFIG = "/network_config/v1"
CONFIG_CRC = "/config/crc/v1"
FACTORY_RESET = "/factory_reset/v1"
ERRORS = "/errors/v1"
OBSERVERS = "/observers/v1"
POINTCLOUD = "/pointcloud/v1"
TRANSMISSION_CODE = "/transmission_code/v1"
LOGIN = "/login/v1"
LOGOUT = "/logout/v1"
REBOOT = "/reboot/v1"

# Lookup table: v1 constant -> {protocol_version: path or None}
# None means the resource does not exist on that protocol version.
RESOURCE_PATHS: dict[str, dict[str, str | None]] = {
    DEVICE_INFO: {"v0": DEVICE_INFO_V0, "v1": DEVICE_INFO},
    STATUS: {"v0": STATUS_V0, "v1": STATUS},
    STATE: {"v0": STATE_V0, "v1": STATE},
    POINTCLOUD: {"v0": POINTCLOUD_V0, "v1": POINTCLOUD},
    NETWORK_CONFIG: {"v0": NETWORK_CONFIG_V0, "v1": NETWORK_CONFIG},
    TRANSMISSION_CODE: {"v0": TRANSMISSION_CODE_V0, "v1": TRANSMISSION_CODE},
    ERRORS: {"v0": ERRORS_V0, "v1": ERRORS},
    OBSERVERS: {"v0": OBSERVERS_V0, "v1": OBSERVERS},
    FACTORY_RESET: {"v0": FACTORY_RESET_V0, "v1": FACTORY_RESET},
    CONFIG_CRC: {"v0": None, "v1": CONFIG_CRC},
    LOGIN: {"v0": None, "v1": LOGIN},
    LOGOUT: {"v0": None, "v1": LOGOUT},
    REBOOT: {"v0": None, "v1": REBOOT},
}
