"""
utils.py

This module provides utility classes and functions for handling point cloud data and publishing it to a Foxglove server.

Features:
- Base and standard point cloud formatters for Foxglove visualization.
- Utility functions for timestamp generation and Euler-to-quaternion conversion.
- A `PointCloudPublisher` class for publishing point cloud data to Foxglove.
- Support for frame transforms for visualization.
"""

import struct
from math import cos, sin
from typing import List, Optional

import foxglove
from foxglove.schemas import (
    FrameTransform,
    FrameTransforms,
    PackedElementField,
    PackedElementFieldNumericType,
    PointCloud,
    Pose,
    Quaternion,
    Timestamp,
    Vector3,
)

from adar_api import Point

TF_TOPIC = "/tf"


class PointCloudFormatter:
    """Formatter for standard point cloud with x, y, z, strength."""

    def __init__(self, frame_id: str = "adar") -> None:
        """Initialize the point cloud formatter.

        Args:
            frame_id: The frame ID for the point cloud data.
        """
        self.frame_id = frame_id
        self.f32 = PackedElementFieldNumericType.Float32
        self.u32 = PackedElementFieldNumericType.Uint32

    @property
    def point_struct(self) -> struct.Struct:
        """Get the struct format for packing point data."""
        return struct.Struct("<ffff")  # x, y, z, strength

    @property
    def point_stride(self) -> int:
        """Get the stride (size in bytes) for each point."""
        return 16  # 4 floats * 4 bytes

    @property
    def fields(self) -> List[PackedElementField]:
        """Get the field definitions for the point cloud."""
        return [
            PackedElementField(name="x", offset=0, type=self.f32),
            PackedElementField(name="y", offset=4, type=self.f32),
            PackedElementField(name="z", offset=8, type=self.f32),
            PackedElementField(name="strength", offset=12, type=self.f32),
        ]

    def pack_point(self, point: Point, buffer: bytearray, offset: int) -> None:
        """Pack a single point into the buffer.

        Args:
            point: The point to pack.
            buffer: The buffer to pack into.
            offset: The offset in the buffer to pack at.
        """
        self.point_struct.pack_into(
            buffer,
            offset,
            point.x,
            point.y,
            point.z,
            float(point.strength),
        )

    def format_points(self, points: List[Point], timestamp: Optional[Timestamp] = None) -> PointCloud:
        """Format points into a Foxglove PointCloud message.

        Args:
            points: List of points to format.
            timestamp: Optional timestamp for the point cloud.

        Returns:
            A formatted PointCloud message.
        """
        buffer = bytearray(self.point_struct.size * len(points))

        for i, point in enumerate(points):
            self.pack_point(point, buffer, i * self.point_struct.size)

        return PointCloud(
            timestamp=timestamp,
            frame_id=self.frame_id,
            pose=Pose(
                position=Vector3(x=0, y=0, z=0),
                orientation=Quaternion(x=0, y=0, z=0, w=1),
            ),
            point_stride=self.point_stride,
            fields=self.fields,
            data=bytes(buffer),
        )


def create_pointcloud_formatter(frame_id: str = "adar") -> PointCloudFormatter:
    """Factory function to create the appropriate point cloud formatter.

    Args:
        frame_id: The frame ID for the point cloud.

    Returns:
        An instance of the appropriate point cloud formatter.
    """
    formatters = {
        "standard": PointCloudFormatter,
    }

    return formatters["standard"](frame_id)


def euler_to_quaternion(roll: float = 0.0, pitch: float = 0.0, yaw: float = 0.0) -> Quaternion:
    """Convert Euler angles to quaternion.

    Args:
        roll: Roll angle in radians.
        pitch: Pitch angle in radians.
        yaw: Yaw angle in radians.

    Returns:
        The quaternion representation of the Euler angles.
    """
    cy = cos(yaw * 0.5)
    sy = sin(yaw * 0.5)
    cp = cos(pitch * 0.5)
    sp = sin(pitch * 0.5)
    cr = cos(roll * 0.5)
    sr = sin(roll * 0.5)

    q = Quaternion(
        x=sr * cp * cy - cr * sp * sy,
        y=cr * sp * cy + sr * cp * sy,
        z=cr * cp * sy - sr * sp * cy,
        w=cr * cp * cy + sr * sp * sy,
    )
    return q


def publish_transforms() -> None:
    """Publish transforms to Foxglove.

    This function publishes the transforms for the coordinate system from the ADAR into the Foxglove base link.
    """
    foxglove.log(
        TF_TOPIC,
        FrameTransforms(
            transforms=[
                FrameTransform(
                    parent_frame_id="base_link",
                    child_frame_id="adar",
                    translation=Vector3(x=0, y=0, z=0),
                    rotation=euler_to_quaternion(roll=1.5708, pitch=0, yaw=1.5708),
                ),
                FrameTransform(
                    parent_frame_id="base_footprint",
                    child_frame_id="base_link",
                    translation=Vector3(x=0, y=0, z=0),
                    rotation=euler_to_quaternion(roll=0, pitch=0, yaw=0),
                ),
            ]
        ),
    )


class PointCloudPublisher:
    """Publisher class for handling pointcloud publishing to Foxglove."""

    def __init__(
        self,
        topic: str,
        frame_id: str = "adar",
        auto_publish_transforms: bool = True,
    ) -> None:
        """Initialize the publisher.

        Args:
            topic: The topic to publish pointclouds to.
            frame_id: The frame ID for the pointcloud.
            auto_publish_transforms: Whether to automatically publish transforms with each pointcloud.
        """
        self.topic = topic
        self.formatter = create_pointcloud_formatter(frame_id)
        self.auto_publish_transforms = auto_publish_transforms

    def publish(self, points: List[Point], timestamp: Optional[Timestamp] = None) -> None:
        """Publish points to Foxglove.

        Args:
            points: List of points to publish.
            timestamp: Optional timestamp for the message.
        """
        pointcloud_msg = self.formatter.format_points(points, timestamp)
        foxglove.log(self.topic, pointcloud_msg)

        if self.auto_publish_transforms:
            publish_transforms()
