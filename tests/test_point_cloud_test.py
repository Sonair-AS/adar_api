from adar_api import CoapPointCloud, DeviceStatus, Point, PointClassification
import logging
import pytest

logger = logging.getLogger(__name__)


def test_parse_point_cloud():
    # Timestamp first, 8 bytes
    payload_bytes = b"\x01\x03\x02\x03\x04\x05\x06\x07"
    # Device status, 8 bytes
    payload_bytes += b"\x01\x03\x02\x03\x04\x05\x06\x07"
    # Point0
    payload_bytes += b"\x34\x12"  # x = 0x1234 = 4660mm
    payload_bytes += b"\x09\x00"  # y = 0x0009  =   9mm
    payload_bytes += b"\x00\x10"  # z = 0x1000 = 4096mm
    payload_bytes += b"\x10\x00"  # strength = 0x0010 = 16
    payload_bytes += b"\x00"  # reserved = 0x00 = 0
    payload_bytes += b"\x07"  # classification = 0x07 = 7

    # Point1
    payload_bytes += b"\x34\x12"  # x = 0x1234 = 4660mm
    payload_bytes += b"\x09\x00"  # y = 0x0009  =   9mm
    payload_bytes += b"\x10\x00"  # z = 0x0010 = 16mm
    payload_bytes += b"\xff\x00"  # strength = 0x00FF = 255
    payload_bytes += b"\x00"  # reserved = 0x00 = 0
    payload_bytes += b"\x01"  # classification = 0x01

    point_cloud = CoapPointCloud(payload_bytes)

    assert point_cloud.timestamp.total_seconds() == pytest.approx(506097522914.230529)
    assert point_cloud.status == DeviceStatus(b"\x01\x03\x02\x03\x04\x05\x06\x07")
    assert len(point_cloud.points) == 2
    assert point_cloud.points[0] == Point(4.66, 0.009, 4.096, 16, PointClassification(7)), (
        f"Point0 {point_cloud.points[0]} not as expected"
    )
    assert point_cloud.points[1] == Point(4.66, 0.009, 0.016, 255, PointClassification(1)), (
        f"Point1 {point_cloud.points[1]} not as expected"
    )


def test_point_classification_bits():
    """Test PointClassification bit parsing including not_classified bit."""
    # Test individual bits
    pc_protective = PointClassification(0x01)
    assert pc_protective.point_in_protective_zone is True
    assert pc_protective.point_in_inner_warning_zone is False
    assert pc_protective.point_in_outer_warning_zone is False
    assert pc_protective.point_in_exclusion_zone is False
    assert pc_protective.not_classified is False

    pc_inner = PointClassification(0x02)
    assert pc_inner.point_in_inner_warning_zone is True
    assert pc_inner.not_classified is False

    pc_outer = PointClassification(0x04)
    assert pc_outer.point_in_outer_warning_zone is True
    assert pc_outer.not_classified is False

    pc_exclusion = PointClassification(0x08)
    assert pc_exclusion.point_in_exclusion_zone is True
    assert pc_exclusion.not_classified is False

    # Test not_classified bit (0x10) - set when no zone preset is configured
    pc_not_classified = PointClassification(0x10)
    assert pc_not_classified.point_in_protective_zone is False
    assert pc_not_classified.point_in_inner_warning_zone is False
    assert pc_not_classified.point_in_outer_warning_zone is False
    assert pc_not_classified.point_in_exclusion_zone is False
    assert pc_not_classified.not_classified is True
    assert "N" in str(pc_not_classified)

    # Test combined bits
    pc_combined = PointClassification(0x07)  # P, I, O
    assert pc_combined.point_in_protective_zone is True
    assert pc_combined.point_in_inner_warning_zone is True
    assert pc_combined.point_in_outer_warning_zone is True
    assert pc_combined.not_classified is False

    # Test string representation
    assert str(PointClassification(0x00)) == "0x00"
    assert str(PointClassification(0x01)) == "0x01(P)"
    assert str(PointClassification(0x10)) == "0x10(N)"
    assert str(PointClassification(0x07)) == "0x07(P,I,O)"


def test_parse_invalid_point_cloud():
    # Arrange

    # Timestamp first, 8 bytes
    payload_bytes = b"\x01\x03\x02\x03\x04\x05\x06\x07"
    # Device status, 8 bytes
    payload_bytes += b"\x01\xff\x02\x03\x04\x05\x06\x07"
    # Point0
    payload_bytes += b"\x34\x12"  # x = 0x1234 = 4660mm
    payload_bytes += b"\x09\x00"  # y = 0x0009  =   9mm
    payload_bytes += b"\x00\x10"  # z = 0x1000 = 4096mm
    payload_bytes += b"\x10\x00"  # strength = 0x0010 = 16
    payload_bytes += b"\x00"  # reserved = 0x00 = 0
    payload_bytes += b"\x07"  # classification = 0x07 = 7

    # Act
    try:
        _ = CoapPointCloud(payload_bytes)
    except Exception:
        logger.exception("Got exception")
        pass
    else:
        assert False, "We expected an exception"
