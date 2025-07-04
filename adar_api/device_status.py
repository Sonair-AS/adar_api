from enum import IntEnum


class DeviceState(IntEnum):
    Init = 1
    SelfTest = 2
    Enabled = 3
    Disabled = 4
    Config = 5
    Error = 6
    Fault = 7


class ZoneStatus:
    """Represents the status of different zones in the ADAR device."""

    def __init__(self, status: int):
        """Initialize ZoneStatus from integer status flags.

        Args:
            status: Integer containing zone status flags as bits
        """
        self.status = status
        self.object_in_protective_zone = (status & 0x01) > 0
        self.object_in_inner_warning_zone = (status & 0x02) > 0
        self.object_in_outer_warning_zone = (status & 0x04) > 0

    def __eq__(self, __value) -> bool:
        return self.status == __value.status

    def __str__(self) -> str:
        msg = f"0x{self.status:X}"
        if self.status != 0:
            msg += "("
            status = []
            if self.object_in_protective_zone:
                status.append("Protective")
            if self.object_in_inner_warning_zone:
                status.append("Inner")
            if self.object_in_outer_warning_zone:
                status.append("Outer")
            msg += ", ".join(status)
            msg += ")"
        return msg


class DeviceStatus:
    """Represents the current status of the ADAR device."""

    def __init__(self, data: bytes):
        """Initialize DeviceStatus from binary data received from the ADAR device.

        Args:
            data: Binary data containing device status information (8 bytes total)

        Raises:
            AssertionError: If data length is not exactly 8 bytes
        """
        assert len(data) == 8, f"Device Status is 8 bytes, got {len(data)}"
        self.data = data
        self.zone_selected = data[0]
        self.device_state = DeviceState(data[1])
        self.transmission_code = data[2]
        self.zone_status = ZoneStatus(data[3])
        self.device_error = int.from_bytes(data[4:], byteorder="little")

    def __str__(self) -> str:
        text = f"Zone:{self.zone_selected}, State:{self.device_state}, Code: {self.transmission_code}, Zone status: {self.zone_status}"
        if self.device_error != 0:
            text += f"Device error: 0x{self.device_error:08X}"
        return text

    def __eq__(self, __value) -> bool:
        return self.data == __value.data
