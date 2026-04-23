"""CoAP resource URIs for the ADAR API.

This module defines the CoAP resource paths for communicating with ADAR devices.

Versioning:
    Resources are versioned (v0, v1, etc.) to allow protocol evolution while
    maintaining backwards compatibility. The Adar class uses the latest version
    (v1) by default.

    - **v0**: Legacy version, kept for backwards compatibility with older scripts
      and firmware. May be removed in future releases.
    - **v1**: Current version used by the Adar class. Recommended for new
      integrations.

Usage:
    For most use cases, use the unversioned constants (e.g., POINTCLOUD, STATUS)
    which point to the latest version. Use versioned constants (e.g., POINTCLOUD_V0)
    only when explicitly targeting older firmware.
"""

# Legacy v0 resources - kept for backwards compatibility with external scripts
DEVICE_INFO_V0 = "/device_info/v0"
STATE_V0 = "/state/v0"
STATUS_V0 = "/status/v0"
NETWORK_CONFIG_V0 = "/network_config/v0"
CONFIG_CRC_V1 = "/config/crc/v1"
FACTORY_RESET_V0 = "/factory_reset/v0"
ERRORS_V0 = "/errors/v0"
OBSERVERS_V0 = "/observers/v0"
POINTCLOUD_V0 = "/pointcloud/v0"
TRANSMISSION_CODE_V0 = "/transmission_code/v0"
LOGIN_V0 = "/login/v0"
LOGOUT_V0 = "/logout/v0"
REBOOT_V0 = "/reboot/v0"

# Latest version
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
