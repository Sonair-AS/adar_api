from struct import unpack


class DeviceErrors:
    """Represents device errors from the ADAR device."""

    def __init__(self, data: bytes):
        """Initialize DeviceErrors from binary data received from the ADAR device.

        Args:
            data: Binary data containing error information, including bitmask and error strings
        """
        # First 4 bytes are error bitmask
        (self.error_bitmask, num_errors) = unpack("<II", data[0 : 4 * 2])

        self.errors = []
        offset = 4 * 2
        for i in range(num_errors):
            next_len = unpack("<I", data[offset : offset + 4])
            error_str = data[offset + 4 : offset + 4 + next_len[0]].decode("utf-8")
            self.errors.append(error_str)
            offset += 4 + next_len[0]

    def __str__(self) -> str:
        if self.error_bitmask == 0:
            return "No errors"

        msg = f"Errors:\n  Bitmask: 0x{self.error_bitmask:08X}"
        if len(self.errors) > 0:
            for error in self.errors:
                msg += f"\n  - {error}"
        return msg
