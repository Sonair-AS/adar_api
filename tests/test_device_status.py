from adar_api import DeviceStatus, DeviceState, ZoneStatus


def test_can_parse_status():
    """
    Test that we can parse the status response.
    """

    # Example status bytes (replace with actual bytes from your device)
    status_bytes = b"\x01\x03\x02\x03\x04\x05\x06\x07"

    status = DeviceStatus(status_bytes)

    print(f"Parsed status: {status}")
    assert status is not None, "Failed to parse status"
    assert status.zone_selected == 1
    assert status.device_state == DeviceState.Enabled
    assert status.zone_status == ZoneStatus(0x03)
    assert status.device_error == 0x07060504

    assert status == DeviceStatus(status_bytes)
