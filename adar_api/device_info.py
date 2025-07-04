def decode_sonair_string(data: bytes) -> tuple[str, bytes]:
    """Decode a length-prefixed string from bytes.

    Args:
        data: Bytes containing length-prefixed string

    Returns:
        Tuple of (decoded_string, remaining_data)
    """
    length = int.from_bytes(data[:4], byteorder="little", signed=False)
    characters = data[4 : 4 + length]
    s = characters.decode("utf-8")
    return s, data[4 + length :]


class DeviceIdentification:
    """Represents device identification information."""

    def __init__(self, serial_number: int, hardware_version: bytes, product_number: str):
        """Initialize device identification information.

        Args:
            serial_number: The device's serial number
            hardware_version: Hardware version as bytes
            product_number: Product number string
        """
        self.serial_number = serial_number
        self.hardware_version = hardware_version
        self.product_number = product_number

    @staticmethod
    def from_bytes(data: bytes) -> tuple["DeviceIdentification", bytes]:
        """Create DeviceIdentification from bytes.

        Args:
            data: Bytes containing device identification data

        Returns:
            Tuple of (DeviceIdentification instance, remaining_data)
        """
        serial_number = int.from_bytes(data[:4], byteorder="little", signed=False)
        hardware_version = data[4:7]
        (product_number, remaining) = decode_sonair_string(data[7:])
        return (
            DeviceIdentification(serial_number, hardware_version, product_number),
            remaining,
        )

    def __str__(self) -> str:
        return f"DeviceIdentification(sn={self.serial_number}, hw={self.hardware_version}, pn={self.product_number})"


class DeviceInfo:
    """Represents device information from the ADAR device."""

    def __init__(self, data: bytes):
        """Initialize DeviceInfo from binary data received from the ADAR device.

        Args:
            data: Binary data containing device information including identification,
                  device name, and firmware version

        Raises:
            AssertionError: If there's remaining data after parsing
        """
        self._data = data
        (self.device_identification, remaining) = DeviceIdentification.from_bytes(data)
        (self.device_name, remaining) = decode_sonair_string(remaining)
        (self.firmware_version, remaining) = decode_sonair_string(remaining)
        assert len(remaining) == 0, f"Remaining data: {remaining}"

    def __str__(self) -> str:
        return f"DeviceInfo(dev={self.device_identification}, name={self.device_name}, fw={self.firmware_version})"
