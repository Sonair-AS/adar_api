"""
ADAR ROS Point Cloud Publisher

This ROS 2 node connects to an ADAR device using CoAP, retrieves point cloud data,
and publishes it as ROS PointCloud2 messages for visualization in Foxglove or other ROS tools.

Features:
- Connects to ADAR device via CoAP
- Publishes point cloud data as sensor_msgs/PointCloud2
- Includes intensity and classification data
- Publishes transform information

Usage:
    ros2 run sonair_adar point_cloud_publisher --ros-args -p device_ip:=<ADAR_IP>

Arguments:
    device_ip: The IP address of the ADAR device (required)

Example:
    ros2 run sonair_adar point_cloud_publisher --ros-args -p device_ip:=10.14.15.68
"""

import asyncio
import sys
from datetime import timedelta
from typing import List

import numpy as np
import rclpy
from aiocoap import Context
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2, PointField
from std_msgs.msg import Header

# Import ADAR API
from adar_api import Adar, Point


class PointCloudRosPublisher(Node):
    """ROS 2 node for publishing ADAR point cloud data."""

    def __init__(self):
        super().__init__("adar_pointcloud_publisher")

        # Declare parameters
        self.declare_parameter("device_ip", "")

        # Get parameters
        self.device_ip = self.get_parameter("device_ip").get_parameter_value().string_value

        if not self.device_ip:
            self.get_logger().error("device_ip parameter is required!")
            raise ValueError("device_ip parameter is required")

        self.get_logger().info(f"Connecting to ADAR device at {self.device_ip}")

        # Create publisher for point clouds
        self.pointcloud_publisher = self.create_publisher(PointCloud2, "/adar/pointcloud", 10)

        # ADAR connection variables - will be initialized by async main
        self.ctx = None
        self.adar = None
        self.running = True

    def convert_timestamp(self, timestamp: timedelta) -> rclpy.time.Time:
        """Convert ADAR timestamp (timedelta) to ROS time."""
        # Convert timedelta to nanoseconds since epoch
        total_seconds = timestamp.total_seconds()
        sec = int(total_seconds)
        nanosec = int((total_seconds - sec) * 1e9)
        return rclpy.time.Time(seconds=sec, nanoseconds=nanosec)

    def points_to_pointcloud2(self, points: List[Point], timestamp: timedelta) -> PointCloud2:
        """Convert ADAR points to ROS PointCloud2 message.

        Args:
            points: List of ADAR Point objects
            timestamp: Timestamp from ADAR device

        Returns:
            PointCloud2 message ready for publishing
        """
        if not points:
            # Create empty point cloud if no points
            header = Header()
            header.frame_id = "adar"
            header.stamp = self.convert_timestamp(timestamp).to_msg()

            return PointCloud2(
                header=header,
                height=1,
                width=0,
                is_dense=True,
                is_bigendian=False,
                fields=[],
                point_step=0,
                row_step=0,
                data=b"",
            )

        # Convert points to numpy array for easier processing
        point_data = []
        for point in points:
            point_data.append(
                [
                    point.x,  # already in meters
                    point.y,  # already in meters
                    point.z,  # already in meters
                    float(
                        point.strength
                    ),  # convert to float to use np.array and same packaging in the PointCloud2 message
                    float(
                        point.classification.value
                    ),  # convert to float to use np.array and same packaging in the PointCloud2 message
                ]
            )

        points_array = np.array(point_data, dtype=np.float32)

        # Define PointCloud2 fields
        ros_dtype = PointField.FLOAT32
        itemsize = np.dtype(np.float32).itemsize  # 4 bytes

        fields = [
            PointField(name="x", offset=0, datatype=ros_dtype, count=1),
            PointField(name="y", offset=itemsize, datatype=ros_dtype, count=1),
            PointField(name="z", offset=2 * itemsize, datatype=ros_dtype, count=1),
            PointField(name="strength", offset=3 * itemsize, datatype=ros_dtype, count=1),
            PointField(name="classification", offset=4 * itemsize, datatype=ros_dtype, count=1),
        ]

        # Create header
        header = Header()
        header.frame_id = "adar"
        header.stamp = self.convert_timestamp(timestamp).to_msg()

        # Pack point data
        point_step = itemsize * 5  # 5 float32 values per point
        row_step = point_step * len(points)
        data = points_array.tobytes()

        # Create PointCloud2 message
        pointcloud2_msg = PointCloud2(
            header=header,
            height=1,
            width=len(points),
            is_dense=True,  # Assuming ADAR provides valid points
            is_bigendian=False,
            fields=fields,
            point_step=point_step,
            row_step=row_step,
            data=data,
        )

        return pointcloud2_msg

    def publish_pointcloud(self, points: List[Point], timestamp: timedelta):
        """Publish point cloud data as PointCloud2 message.

        Args:
            points: List of ADAR Point objects
            timestamp: Timestamp from ADAR device
        """
        try:
            # Convert to PointCloud2
            pointcloud2_msg = self.points_to_pointcloud2(points, timestamp)

            # Publish the message
            self.pointcloud_publisher.publish(pointcloud2_msg)

        except Exception as e:
            self.get_logger().error(f"Error publishing point cloud: {e}")


async def async_main(node: PointCloudRosPublisher):
    """
    Main asynchronous entry point
    """
    print("Starting CoAP observer...")

    try:
        await coap_loop(node)
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


async def coap_loop(node: PointCloudRosPublisher):
    """
    Observes point cloud data from ADAR and publishes it to the pointcloud topic
    """
    msg_count = 0

    # Create a CoAP client context
    node.ctx = await Context.create_client_context()

    # Initialize the ADAR connection
    node.adar = Adar(node.ctx, node.device_ip)

    # Observe point cloud data and publish it
    async for coap_msg in node.adar.observe_point_cloud():
        node.publish_pointcloud(coap_msg.points, coap_msg.timestamp)
        msg_count += 1

        if msg_count % 100 == 0 or msg_count == 1:
            print(f"Published {msg_count} messages.")

        # Allow ROS to process callbacks
        rclpy.spin_once(node, timeout_sec=0)


def main(args=None):
    """Main entry point for the ROS node."""
    rclpy.init(args=args)

    try:
        node = PointCloudRosPublisher()

        # Run asyncio loop in main thread
        asyncio.run(async_main(node))

    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
    finally:
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
