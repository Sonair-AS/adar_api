"""
utils.py

This module provides utility classes and functions for handling point cloud data and publishing it to a Foxglove server.

Features:
- Base and standard point cloud formatters for Foxglove visualization.
- Utility functions for timestamp generation and Euler-to-quaternion conversion.
- A `PointCloudPublisher` class for publishing point cloud data to Foxglove.
- Support for frame transforms for visualization.
"""

from datetime import timedelta
import struct
from math import cos, sin
from typing import List, Optional

import foxglove
from foxglove.channels import SceneUpdateChannel
from foxglove.schemas import (
    Color,
    FrameTransform,
    FrameTransforms,
    PackedElementField,
    PackedElementFieldNumericType,
    Point3,
    PointCloud,
    Pose,
    Quaternion,
    SceneEntity,
    SceneUpdate,
    Timestamp,
    TriangleListPrimitive,
    Vector3,
)

from adar_api import Point
from adar_api.device_status import DeviceStatus

TF_TOPIC = "/tf"


class PointCloudFormatter:
    """Formatter for standard point cloud with x, y, z, strength, and classification."""

    def __init__(self, frame_id: str = "adar") -> None:
        """Initialize the point cloud formatter.

        Args:
            frame_id: The frame ID for the point cloud data.
        """
        self.frame_id = frame_id
        self.f32 = PackedElementFieldNumericType.Float32
        self.u8 = PackedElementFieldNumericType.Uint8
        self.u16 = PackedElementFieldNumericType.Uint16
        self.u32 = PackedElementFieldNumericType.Uint32

    @property
    def point_struct(self) -> struct.Struct:
        """Get the struct format for packing point data."""
        return struct.Struct("<fffHB")  # x, y, z, strength, classification

    @property
    def point_stride(self) -> int:
        """Get the stride (size in bytes) for each point."""
        return 15  # 3 floats * 4 bytes + 1 uint16 * 2 bytes + 1 uint8 * 1 byte

    @property
    def fields(self) -> List[PackedElementField]:
        """Get the field definitions for the point cloud."""
        return [
            PackedElementField(name="x", offset=0, type=self.f32),
            PackedElementField(name="y", offset=4, type=self.f32),
            PackedElementField(name="z", offset=8, type=self.f32),
            PackedElementField(name="strength", offset=12, type=self.u16),
            PackedElementField(name="classification", offset=14, type=self.u8),
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
            point.strength,
            point.classification.value,
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

    def convert_timestamp(self, timestamp: Optional[timedelta]) -> Optional[Timestamp]:
        """Convert a timedelta to a Foxglove timestamp."""
        if timestamp is None:
            return None

        total_seconds = timestamp.total_seconds()
        sec = int(total_seconds)
        nsec = int((total_seconds - sec) * 1_000_000_000)  # Convert fractional seconds to nanoseconds
        return Timestamp(sec=sec, nsec=nsec)

    def publish(self, points: List[Point], timestamp: Optional[timedelta] = None) -> None:
        """Publish points to Foxglove.

        Args:
            points: List of points to publish.
            timestamp: Optional timestamp for the message.
        """
        foxglove_timestamp = self.convert_timestamp(timestamp)

        pointcloud_msg = self.formatter.format_points(points, foxglove_timestamp)
        foxglove.log(self.topic, pointcloud_msg)

        if self.auto_publish_transforms:
            publish_transforms()


class ZoneFormatter:
    """Formatter for configuration data visualization."""

    def __init__(self):
        """
        Initialize the zone formatter.
        """

    def create_marker(self, zone_dict, color=None):
        """
        Create a Foxglove SceneUpdate with TriangleListPrimitive for the zone.
        The zone polygons are built with multiple triangles.

        Args:
            zone_dict: Dictionary with 'polygon' (containing 'points') and 'yspan' (containing 'min'/'max')
            color: Color for the zone (default: semi-transparent green)

        Returns:
            List of TriangleListPrimitive objects for Foxglove logging
        """
        if not zone_dict:
            return None

        # Default color: semi-transparent green
        if color is None:
            color = Color(r=0.0, g=1.0, b=0.0, a=0.3)

        # Extract polygon points and Y-span from dict
        polygon_data = zone_dict.get("polygon", {})
        points_data = polygon_data.get("points", [])
        yspan_data = zone_dict.get("yspan", {})

        if not points_data or not yspan_data:
            return None

        polygon_points_x = [p["x"] for p in points_data]
        polygon_points_z = [p["z"] for p in points_data]

        y_min = yspan_data["min"]
        y_max = yspan_data["max"]

        # Triangles base
        triangles = []
        for i in range(1, len(polygon_points_x) - 1):
            triangle = TriangleListPrimitive(
                pose=Pose(
                    position=Vector3(x=0.0, y=0.0, z=0.0),
                    orientation=Quaternion(x=0.0, y=0.0, z=0.0, w=1.0),
                ),
                points=[
                    Point3(x=polygon_points_x[0], y=y_min, z=polygon_points_z[0]),
                    Point3(x=polygon_points_x[i], y=y_min, z=polygon_points_z[i]),
                    Point3(x=polygon_points_x[i + 1], y=y_min, z=polygon_points_z[i + 1]),
                ],
                color=color,
            )
            triangles.append(triangle)

        # Triangles top
        for i in range(1, len(polygon_points_x) - 1):
            triangle = TriangleListPrimitive(
                pose=Pose(
                    position=Vector3(x=0.0, y=0.0, z=0.0),
                    orientation=Quaternion(x=0.0, y=0.0, z=0.0, w=1.0),
                ),
                points=[
                    Point3(x=polygon_points_x[0], y=y_max, z=polygon_points_z[0]),
                    Point3(x=polygon_points_x[i], y=y_max, z=polygon_points_z[i]),
                    Point3(x=polygon_points_x[i + 1], y=y_max, z=polygon_points_z[i + 1]),  # Left point
                ],
                color=color,
            )
            triangles.append(triangle)

        # Trianlges sides
        for i in range(len(polygon_points_x)):
            j = (i + 1) % len(polygon_points_x)
            triangle = TriangleListPrimitive(
                pose=Pose(
                    position=Vector3(x=0.0, y=0.0, z=0.0),
                    orientation=Quaternion(x=0.0, y=0.0, z=0.0, w=1.0),
                ),
                points=[
                    Point3(x=polygon_points_x[i], y=y_min, z=polygon_points_z[i]),
                    Point3(x=polygon_points_x[j], y=y_min, z=polygon_points_z[j]),
                    Point3(x=polygon_points_x[j], y=y_max, z=polygon_points_z[j]),
                ],
                color=color,
            )
            triangles.append(triangle)
            triangle = TriangleListPrimitive(
                pose=Pose(
                    position=Vector3(x=0.0, y=0.0, z=0.0),
                    orientation=Quaternion(x=0.0, y=0.0, z=0.0, w=1.0),
                ),
                points=[
                    Point3(x=polygon_points_x[i], y=y_max, z=polygon_points_z[i]),
                    Point3(x=polygon_points_x[j], y=y_max, z=polygon_points_z[j]),
                    Point3(x=polygon_points_x[i], y=y_min, z=polygon_points_z[i]),
                ],
                color=color,
            )
            triangles.append(triangle)

        return triangles


class ZonePublisher:
    """Publisher class for handling zone publishing to Foxglove with caching."""

    def __init__(self, topic="/adar/zone"):
        """
        Initialize the zone publisher.

        Args:
            topic: Topic to publish configuration data to
        """
        self.topic = topic
        self._formatter = ZoneFormatter()
        self.protective_scene_channel = SceneUpdateChannel(self.topic + "/protective_zone")
        self.inner_warning_scene_channel = SceneUpdateChannel(self.topic + "/inner_warning_zone")
        self.outer_warning_scene_channel = SceneUpdateChannel(self.topic + "/outer_warning_zone")

        # Active zone tracking
        self._active_zone_id = 0
        self._cached_config = None

        # Cache for markers to avoid recalculation
        self._cached_protective_markers = None
        self._cached_inner_warning_markers = None
        self._cached_outer_warning_markers = None

    def get_active_zone(self) -> int:
        """
        Get the current active zone ID.

        Returns:
            The active zone ID
        """
        return self._active_zone_id

    def set_active_zone(self, zone_id: int) -> bool:
        """
        Set the active zone ID and recalculate markers if changed.

        Args:
            zone_id: The zone preset ID to activate

        Returns:
            True if zone changed and recalculation needed, False otherwise
        """
        if self._active_zone_id != zone_id:
            self._active_zone_id = zone_id
            # Recalculate markers with the new active zone
            if self._cached_config:
                self._update_markers_for_active_zone()
            return True
        return False

    def _update_markers_for_active_zone(self) -> None:
        """
        Update markers based on the current active zone from cached config.
        Internal method called when active zone changes.
        """
        if not self._cached_config:
            return

        zone_presets = self._cached_config.get("zonePresets", [])
        if not zone_presets:
            self._cached_protective_markers = None
            self._cached_inner_warning_markers = None
            self._cached_outer_warning_markers = None
            return

        # Get the active zone preset by ID
        if self._active_zone_id >= len(zone_presets):
            print(
                f"Warning: Active zone ID {self._active_zone_id} not found in config (only {len(zone_presets)} presets available)"
            )
            return

        zone_preset = zone_presets[self._active_zone_id]
        self._calculate_markers(zone_preset)

    def _calculate_markers(self, zone_preset: dict) -> None:
        """
        Calculate markers for a given zone preset.

        Args:
            zone_preset: Zone preset dictionary with protective, inner_warning, and outer_warning zones
        """
        # Get zone definitions from preset
        protective_zone = zone_preset.get("protectiveZone")
        inner_warning_zone = zone_preset.get("innerWarningZone")
        outer_warning_zone = zone_preset.get("outerWarningZone")

        # Calculate markers for each zone
        if protective_zone:
            self._cached_protective_markers = self._formatter.create_marker(
                protective_zone,
                color=Color(r=1.0, g=0.0, b=0.0, a=0.6),  # Red
            )
        else:
            self._cached_protective_markers = None

        if inner_warning_zone:
            self._cached_inner_warning_markers = self._formatter.create_marker(
                inner_warning_zone,
                color=Color(r=1.0, g=0.5, b=0.0, a=0.4),  # Orange
            )
        else:
            self._cached_inner_warning_markers = None

        if outer_warning_zone:
            self._cached_outer_warning_markers = self._formatter.create_marker(
                outer_warning_zone,
                color=Color(r=1.0, g=1.0, b=0.0, a=0.3),  # Yellow
            )
        else:
            self._cached_outer_warning_markers = None

    def update_zones(self, config_dict) -> None:
        """
        Update zone markers from configuration dictionary.
        Call this when the configuration has changed.

        Args:
            config_dict: Configuration dictionary containing 'zonePresets' with zone definitions
        """
        # Cache the config for potential active zone changes
        self._cached_config = config_dict

        # Extract zone preset based on active_zone_id
        zone_presets = config_dict.get("zonePresets", [])
        if not zone_presets:
            self._cached_protective_markers = None
            self._cached_inner_warning_markers = None
            self._cached_outer_warning_markers = None
            return

        # Get the active zone preset by ID
        if self._active_zone_id >= len(zone_presets):
            print(f"Warning: Active zone ID {self._active_zone_id} not found, using zone 0")
            zone_preset = zone_presets[0]
        else:
            zone_preset = zone_presets[self._active_zone_id]

        # Calculate markers for this zone preset
        self._calculate_markers(zone_preset)

    def publish(self) -> None:
        """
        Publish cached zone markers to Foxglove.
        Call update_zones() first to calculate/update the markers.
        """
        # Publish cached markers
        if self._cached_protective_markers:
            self.protective_scene_channel.log(
                SceneUpdate(entities=[SceneEntity(frame_id="adar", triangles=self._cached_protective_markers)])
            )

        if self._cached_inner_warning_markers:
            self.inner_warning_scene_channel.log(
                SceneUpdate(
                    entities=[
                        SceneEntity(
                            frame_id="adar",
                            triangles=self._cached_inner_warning_markers,
                        )
                    ]
                )
            )

        if self._cached_outer_warning_markers:
            self.outer_warning_scene_channel.log(
                SceneUpdate(
                    entities=[
                        SceneEntity(
                            frame_id="adar",
                            triangles=self._cached_outer_warning_markers,
                        )
                    ]
                )
            )


class DeviceStatusFormatter:
    """Formatter for device status."""

    def __init__(self):
        """
        Initialize the device status formatter.
        """

    def create_msg(self, device_status: DeviceStatus) -> dict:
        """
        Create a dictionary message from DeviceStatus object.

        Args:
            device_status: DeviceStatus object to format

        Returns:
            Dictionary containing formatted device status information
        """
        return {
            "zone_selected": device_status.zone_selected,
            "device_state": str(device_status.device_state),
            "device_state_value": int(device_status.device_state),
            "transmission_code": device_status.transmission_code,
            "zone_status": {
                "value": device_status.zone_status.status,
                "object_in_protective_zone": device_status.zone_status.object_in_protective_zone,
                "object_in_inner_warning_zone": device_status.zone_status.object_in_inner_warning_zone,
                "object_in_outer_warning_zone": device_status.zone_status.object_in_outer_warning_zone,
            },
            "device_error": device_status.device_error,
            "status_string": str(device_status),
        }


class DeviceStatusPublisher:
    """Publisher class for handling device status publishing to Foxglove."""

    def __init__(self, topic="/adar/device_status"):
        """
        Initialize the device status publisher.

        Args:
            topic: Topic to publish device status to
        """
        self.topic = topic
        self._formatter = DeviceStatusFormatter()

    def publish(self, device_status: DeviceStatus) -> None:
        """
        Publish device status to Foxglove.

        Args:
            device_status: DeviceStatus object to publish
        """
        msg = self._formatter.create_msg(device_status)
        foxglove.log(self.topic, msg)
