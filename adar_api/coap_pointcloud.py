"""
This file contains the functions used to extract a point cloud and status from
the payload in a CoAP message; it is assumed that the coap specific parts of
the message have been removed before calling these functions.

The payload is a byte array which looks like this:

[ b0, b1, b2, b3, b4, b5, b6, b7, b8, b9, b10, b11, b12, b13, b14, b15, b16, b17, b18, b19, b20, b21, b22, b23, b24, b25 ...]
  |____________________________|  |__________________________________|  |______|  |_______| |______|  |______| |__| |__|

   Timestamp(uint64)                   Device status (8 bytes)          x(int16)  y(int16)  z(int16)  s(uint16) r(uint8) c(uint8)

                                                                         |_____________________________________________| |_______

                                                                                 point 0                                   point 1


x, y, z are cartesian coordinates with distance in millimeters and are encoded as 16-bit signed integers. Note: the Python class will convert these to meters.
s is the strength of the point and is encoded as a 16-bit unsigned integer.
r is reserved and shall be ignored.
c is point classification and is encoded as a 8-bit unsigned integer. See PointClassification class for details.


All values in payload are encoded as little endian.
"""

import logging
import math
import struct
from datetime import timedelta
from typing import List, Tuple

from .device_status import DeviceStatus

logger = logging.getLogger(__name__)


class PointClassification:
    def __init__(self, value: int):
        """Initialize point classification from integer value.

        Args:
            value: Integer value representing point classification flags
        """
        self.value = value
        self.point_in_protective_zone = value & 0x01
        self.point_in_inner_warning_zone = value & 0x02
        self.point_in_outer_warning_zone = value & 0x04
        self.point_in_exclusion_zone = value & 0x08

    def __str__(self) -> str:
        text = f"0x{self.value:02X}"
        if self.value != 0:
            text += "("
            fields = []
            if self.point_in_protective_zone:
                fields.append("P")
            if self.point_in_inner_warning_zone:
                fields.append("I")
            if self.point_in_outer_warning_zone:
                fields.append("O")
            if self.point_in_exclusion_zone:
                fields.append("E")
            text += ",".join(fields)
            text += ")"
        return text

    def __eq__(self, other) -> bool:
        return self.value == other.value


class Point:
    """Represents a single 3D point in the point cloud."""

    def __init__(
        self,
        x: float,  # Converted from int16 in mm to float in meters
        y: float,  # Converted from int16 in mm to float in meters
        z: float,  # Converted from int16 in mm to float in meters
        strength: int,
        classification: PointClassification,
    ):
        """Initialize a 3D point with position, strength, and classification.

        Args:
            x: X coordinate in meters
            y: Y coordinate in meters
            z: Z coordinate in meters
            strength: Signal strength of the point
            classification: Point classification flags
        """
        self.x = x
        self.y = y
        self.z = z
        self.strength = strength
        self.classification = classification

    @property
    def r(self) -> float:
        """The radial distance from the sensor to the point."""
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    def __str__(self) -> str:
        return f"{self.x:.2f}, {self.y:.2f}, {self.z:.2f}, {self.strength}, {self.classification})"

    def __eq__(self, __value) -> bool:
        epsilon = 1e-3
        return (
            abs(self.x - __value.x) < epsilon
            and abs(self.y - __value.y) < epsilon
            and abs(self.z - __value.z) < epsilon
            and self.strength == __value.strength
            and self.classification == __value.classification
        )


class CoapPointCloud:
    """
    CoAP Point Cloud class for handling point cloud data.
    """

    def __init__(self, coap_payload: bytes):
        """Initialize CoapPointCloud from CoAP payload bytes.

        Args:
            coap_payload: Binary payload containing timestamp, device status, and point cloud data

        Raises:
            ValueError: If the payload cannot be decoded
            struct.error: If there's an error in the binary data structure
            AssertionError: If the payload format is invalid
        """
        try:
            self.points = []
            (self.timestamp, self.status) = self._parse_payload(coap_payload)
        except (ValueError, struct.error, AssertionError) as e:
            logger.exception(
                f"Failed to decode {len(coap_payload)} bytes into CoapPointCloud - first 26 bytes: {coap_payload[:26].hex()}: {e}"
            )
            raise

    def __str__(self) -> str:
        return f"{self.status}-{len(self.points)} points"

    def __list__(self) -> List[Point]:
        return self.points

    def __len__(self) -> int:
        return len(self.points)

    def _parse_payload(
        self,
        payload: bytes,
    ) -> tuple[timedelta, DeviceStatus]:
        """Extract the status and the pointcloud from the bytes in the payload.

        Args:
            payload: Raw bytes payload

        Returns:
            Tuple of (timestamp, status) where timestamp is a timedelta and status is a DeviceStatus object
        """
        timestamp, state_data, point_data = split_coap_payload(payload)

        us = struct.unpack("<Q", timestamp)[0]
        dt = timedelta(microseconds=us)

        try:
            status = DeviceStatus(state_data)
        except (ValueError, AssertionError) as e:
            logger.exception(f"Failed to decode '{state_data}'  into DeviceStatus: {e}")
            raise

        if len(point_data) > 0:
            assert len(point_data) % 10 == 0, f"Expected data length to be a multiple of 10, got {len(point_data)}"

            for i in range(0, len(point_data), 10):
                [x_mm, y_mm, z_mm, strength] = struct.unpack("<hhhH", point_data[i : i + 8])
                _reserved = point_data[i + 8]
                classification = PointClassification(point_data[i + 9])
                self.points.append(Point(x_mm / 1000, y_mm / 1000, z_mm / 1000, strength, classification))

        return dt, status


def split_coap_payload(payload: bytes) -> Tuple[bytes, bytes, bytes]:
    """Split the payload into timestamp, status, and point data arrays.

    Args:
        payload: Raw bytes payload

    Returns:
        Tuple of (timestamp_data, status_data, point_data)
    """
    TIMESTAMP_OFFSET = 0
    TIMESTAMP_LENGTH = 8
    STATUS_OFFSET = TIMESTAMP_OFFSET + TIMESTAMP_LENGTH
    STATUS_LENGTH = 8
    DATA_OFFSET = STATUS_OFFSET + STATUS_LENGTH

    timestamp = payload[TIMESTAMP_OFFSET : TIMESTAMP_OFFSET + TIMESTAMP_LENGTH]
    status_data = payload[STATUS_OFFSET : STATUS_OFFSET + STATUS_LENGTH]
    point_data = payload[DATA_OFFSET:]
    return timestamp, status_data, point_data
