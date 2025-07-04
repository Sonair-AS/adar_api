from .duration import Duration


class Statistics:
    """Represents statistics of the ADAR device."""

    def __init__(self, data: bytes):
        """Initialize Statistics from binary data received from the ADAR device.

        Args:
            data: Binary data containing statistics information (44 bytes total)
        """
        self._data = data
        self._up_time = Duration(data[:12])
        self.total_number_of_pings = int.from_bytes(data[12:20], byteorder="little", signed=False)
        self.pings_with_object_in_protective_zone = int.from_bytes(data[20:28], byteorder="little", signed=False)
        self.pings_with_object_in_inner_warning_zone = int.from_bytes(data[28:36], byteorder="little", signed=False)
        self.pings_with_object_in_outer_warning_zone = int.from_bytes(data[36:44], byteorder="little", signed=False)

    @property
    def up_time(self) -> Duration:
        """Get device uptime."""
        return self._up_time

    def __str__(self) -> str:
        return f"up_time:{self.up_time}, total_number_of_pings:{self.total_number_of_pings}, pings_with_object_in_protective_zone:{self.pings_with_object_in_protective_zone}, pings_with_object_in_inner_warning_zone:{self.pings_with_object_in_inner_warning_zone}, pings_with_object_in_outer_warning_zone:{self.pings_with_object_in_outer_warning_zone}"

    def __repr__(self) -> str:
        return f"Statistics({self})"
