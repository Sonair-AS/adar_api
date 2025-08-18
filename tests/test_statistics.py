from adar_api.statistics import Statistics
import struct


def test_decode_statistics():
    # Arrange
    data = (
        struct.pack("<Q", 3600)  # up_time seconds (8 bytes)
        + struct.pack("<I", 500_000_000)  # up_time nanoseconds (4 bytes)
        + struct.pack("<Q", 10_000)  # total_number_of_pings (8 bytes)
        + struct.pack("<Q", 150)  # pings_with_object_in_protective_zone (8 bytes)
        + struct.pack("<Q", 300)  # pings_with_object_in_inner_warning_zone (8 bytes)
        + struct.pack("<Q", 500)  # pings_with_object_in_outer_warning_zone (8 bytes)
    )

    # Act
    statistics = Statistics(data)

    # Assert
    assert statistics.up_time.total_seconds == 3600.5
    assert statistics.up_time.secs == 3600
    assert statistics.up_time.nanos == 500_000_000
    assert statistics.total_number_of_pings == 10_000
    assert statistics.pings_with_object_in_protective_zone == 150
    assert statistics.pings_with_object_in_inner_warning_zone == 300
    assert statistics.pings_with_object_in_outer_warning_zone == 500
