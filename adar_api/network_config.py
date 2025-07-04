import struct

FLAG_STATIC_IP = 0x01
FLAG_SYNC_ENABLED = 0x02
FLAG_SYNC_SERVER_ENABLED = 0x04


class NetworkConfig:
    """Network configuration class for parsing and creating network config data"""

    def __init__(
        self,
        data: bytes = None,
        *,
        dhcp_enabled: bool = True,
        static_ip: str = "10.20.30.40",
        subnet_mask: str = "255.255.255.0",
        gateway: str = "10.20.30.1",
        sync_server_ip: str = "0.0.0.0",
        device_tag: str = "",
        sync_enabled: bool = False,
        sync_server_enabled: bool = False,
    ):
        """
        Initialize NetworkConfig either from bytes or from individual parameters.

        Args:
            data: 84+ bytes containing network configuration
            dhcp_enabled: Whether DHCP is enabled (ignored if data provided)
            static_ip: Static IP address string (ignored if data provided)
            subnet_mask: Subnet mask string (ignored if data provided)
            gateway: Gateway IP address string (ignored if data provided)
            sync_server_ip: Synchronization server IP address string (ignored if `data` is provided and if `sync_server_enabled` is True or `sync_enabled` is False	)
            device_tag: Device tag string (ignored if data provided)
            sync_enabled: Whether sync is enabled (ignored if data provided)
            sync_server_enabled: Whether device is sync server (ignored if `data` is provided and if `sync_enabled` is False)
        """
        if data is not None:
            self._parse_from_data(data)
        else:
            self._parse_from_params(
                dhcp_enabled,
                static_ip,
                subnet_mask,
                gateway,
                sync_server_ip,
                device_tag,
                sync_enabled,
                sync_server_enabled,
            )

    def _parse_from_data(self, data: bytes):
        """Parse network configuration from bytes.

        Args:
            data: Binary data containing network configuration
        """
        assert len(data) >= 20 + 64, f"Network config data should be at least 84 bytes, got {len(data)}"
        self.data = data

        (
            cfg_flags,
            static_ip_bytes,
            subnet_mask_bytes,
            gateway_bytes,
            sync_server_ip_bytes,
        ) = struct.unpack_from("<I4s4s4s4s", data)

        self.cfg_flags = cfg_flags
        self.dhcp_enabled = not bool(cfg_flags & 0x01)  # Flag 0x01 means static IP (not DHCP)
        self.sync_enabled = bool(cfg_flags & FLAG_SYNC_ENABLED)
        self.sync_server_enabled = bool(cfg_flags & FLAG_SYNC_SERVER_ENABLED)
        self.static_ip = ".".join(map(str, static_ip_bytes))
        self.subnet_mask = ".".join(map(str, subnet_mask_bytes))
        self.gateway = ".".join(map(str, gateway_bytes))
        self.sync_server_ip = ".".join(map(str, sync_server_ip_bytes))
        # Device tag is a 0-terminated string of up to 128 bytes that follows after 64 bytes of reserved space
        self.device_tag = data[20 + 64 : 20 + 64 + 128].decode("utf-8").rstrip("\0")

    def _parse_from_params(
        self,
        dhcp_enabled: bool,
        static_ip: str,
        subnet_mask: str,
        gateway: str,
        sync_server_ip: str,
        device_tag: str,
        sync_enabled: bool,
        sync_server_enabled: bool,
    ):
        """Parse network configuration from individual parameters.

        Args:
            dhcp_enabled: Whether DHCP is enabled
            static_ip: Static IP address string
            subnet_mask: Subnet mask string
            gateway: Gateway IP address string
            sync_server_ip: Sync server IP address string
            device_tag: Device tag string
            sync_enabled: Whether sync is enabled
            sync_server_enabled: Whether device is sync server
        """
        self.dhcp_enabled = dhcp_enabled
        self.static_ip = static_ip
        self.subnet_mask = subnet_mask
        self.gateway = gateway
        self.sync_server_ip = sync_server_ip
        self.device_tag = device_tag
        self.sync_enabled = sync_enabled
        self.sync_server_enabled = sync_server_enabled

        # Set flags: 0x01 bit means static IP (not DHCP)
        self.cfg_flags = 0x00 if dhcp_enabled else FLAG_STATIC_IP
        self.cfg_flags |= FLAG_SYNC_ENABLED if sync_enabled else 0x00
        self.cfg_flags |= FLAG_SYNC_SERVER_ENABLED if sync_server_enabled else 0x00

        # Pack into binary format
        static_ip_bytes = bytes(map(int, static_ip.split(".")))
        subnet_mask_bytes = bytes(map(int, subnet_mask.split(".")))
        gateway_bytes = bytes(map(int, gateway.split(".")))
        sync_server_ip_bytes = bytes(map(int, sync_server_ip.split(".")))

        self.data = struct.pack(
            "<I4s4s4s4s",
            self.cfg_flags,
            static_ip_bytes,
            subnet_mask_bytes,
            gateway_bytes,
            sync_server_ip_bytes,
        )
        # Add 64 bytes of zeros for reserved space
        self.data += bytes([0] * 64)
        # Add device tag with null terminator
        self.data += device_tag.encode("utf-8") + b"\0"

    def encode(self) -> bytes:
        """Return the network configuration as bytes.

        Returns:
            Binary representation of the network configuration
        """
        return self.data

    def __str__(self) -> str:
        dhcp_status = "Yes" if self.dhcp_enabled else "No"
        sync_status = "Yes" if self.sync_enabled else "No"
        sync_server_status = "Yes" if self.sync_server_enabled else "No"
        return (
            f"Network Configuration:\n"
            f"  DHCP Enabled:      {dhcp_status}\n"
            f"  Static IP address: {self.static_ip}\n"
            f"  Gateway:           {self.gateway}\n"
            f"  Subnet mask:       {self.subnet_mask}\n"
            f"  Sync server IP:    {self.sync_server_ip}\n"
            f"  Sync Enabled:      {sync_status}\n"
            f"  Sync Server:       {sync_server_status}"
        )

    def __eq__(self, other) -> bool:
        if not isinstance(other, NetworkConfig):
            return False
        return self.data == other.data
