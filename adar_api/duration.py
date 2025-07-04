from datetime import timedelta


class Duration:
    """Represents a duration of time."""

    def __init__(self, data: bytes):
        """Initialize Duration from binary data.

        Args:
            data: Binary data containing duration information (12 bytes total)
                  First 8 bytes: seconds (little-endian unsigned 64-bit integer)
                  Next 4 bytes: nanoseconds (little-endian unsigned 32-bit integer)
        """
        self._data = data
        self.secs = int.from_bytes(data[:8], byteorder="little", signed=False)
        self.nanos = int.from_bytes(data[8:12], byteorder="little", signed=False)
        self._timedelta = timedelta(seconds=self.secs + self.nanos / 1e9)

    @property
    def total_seconds(self) -> float:
        return self._timedelta.total_seconds()

    @property
    def total_milliseconds(self) -> int:
        return int(self._timedelta.total_seconds() * 1000)

    @property
    def total_microseconds(self) -> int:
        return int(self._timedelta.total_seconds() * 1_000_000)

    @property
    def total_nanoseconds(self) -> int:
        return int(self._timedelta.total_seconds() * 1_000_000_000)

    def __str__(self) -> str:
        total_seconds = self._timedelta.total_seconds()
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = total_seconds % 60

        if hours > 0:
            return f"{hours}h {minutes}m {seconds:.2f}s"
        elif minutes > 0:
            return f"{minutes}m {seconds:.2f}s"
        else:
            return f"{seconds:.2f}s"

    def __repr__(self) -> str:
        return f"Duration({self._timedelta})"
