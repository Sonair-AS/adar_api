"""
Launch file for ADAR point cloud publisher.

This launch file starts:
- ADAR ROS2 point cloud publisher node
- Static transforms to convert from ADAR frame to ROS standard coordinate system
- Foxglove bridge for visualization

Usage:
    ros2 launch sonair_adar sonair_adar.launch.py device_ip:=<ADAR_IP_ADDRESS>

Parameters:
    device_ip: IP address of the ADAR (required)
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_xml.launch_description_sources import XMLLaunchDescriptionSource


def generate_launch_description():
    return LaunchDescription(
        [
            # Declare launch arguments
            DeclareLaunchArgument(
                "device_ip", default_value="", description="IP address of the ADAR (required - e.g., 10.20.30.40)"
            ),
            # Foxglove bridge
            IncludeLaunchDescription(
                XMLLaunchDescriptionSource(
                    os.path.join(get_package_share_directory("foxglove_bridge"), "launch", "foxglove_bridge_launch.xml")
                ),
            ),
            # Static transform: base_footprint → base_link
            Node(
                package="tf2_ros",
                executable="static_transform_publisher",
                name="base_footprint_to_base_link",
                arguments=["0", "0", "0", "0", "0", "0", "base_footprint", "base_link"],
                output="screen",
            ),
            # Static transform: base_link → adar (rotate to ROS standard coordinate system)
            # Rotations: roll=90°, pitch=0°, yaw=90° to align ADAR frame with ROS conventions
            Node(
                package="tf2_ros",
                executable="static_transform_publisher",
                name="base_link_to_adar",
                arguments=["0", "0", "0", "1.5708", "0", "1.5708", "base_link", "adar"],
                output="screen",
            ),
            # ADAR point cloud publisher node
            # Publishes point cloud data to /adar/pointcloud topic
            Node(
                package="sonair_adar",
                executable="point_cloud_publisher",
                name="adar_pointcloud_publisher",
                namespace="adar",
                output="screen",
                parameters=[
                    {
                        "device_ip": LaunchConfiguration("device_ip"),
                    }
                ],
                emulate_tty=True,
            ),
        ]
    )
