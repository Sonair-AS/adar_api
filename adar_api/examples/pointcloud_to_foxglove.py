"""
pointcloud_to_foxglove.py

This script connects to an ADAR device using CoAP, retrieves point cloud data, and publishes it to a Foxglove server.

Features:
- Initializes a Foxglove server for visualization.
- Observes point cloud data from an ADAR device via CoAP.
- Publishes point cloud data to a specified topic.

Usage:
    python pointcloud_to_foxglove.py <ipaddr> [--foxglove-host <host>]

Arguments:
    ipaddr: The IP address of the ADAR device.
    --foxglove-host: The host IP address for the Foxglove server (default: 127.0.0.1).

Example:
    python pointcloud_to_foxglove.py 10.14.15.68 --foxglove-host 127.0.0.2
"""

import argparse
import asyncio
import sys

import foxglove
from aiocoap import Context

from adar_api import Adar
from adar_api.examples.utils import PointCloudPublisher

# Define the topic for publishing point cloud data
POINTCLOUD_TOPIC = "/adar/pointcloud"


async def async_main() -> None:
    """
    Main asynchronous entry point for the script.

    - Parses command-line arguments.
    - Initializes the Foxglove server.
    - Starts the CoAP loop to observe and publish point cloud data.

    Raises:
        SystemExit: If required arguments are missing or invalid.
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Pointcloud Publisher for ADAR devices.")
    parser.add_argument(
        "ipaddr",
        type=str,
        help="IP address of the ADAR device",
    )
    parser.add_argument(
        "--foxglove-host",
        type=str,
        default="127.0.0.1",
        help="Host IP address for the Foxglove server (default: 127.0.0.1)",
    )
    args = parser.parse_args()

    # Initialize the Foxglove server
    foxglove.start_server(host=args.foxglove_host)

    # Start the CoAP loop to observe and publish point cloud data
    try:
        await coap_loop(args)
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


async def coap_loop(args) -> None:
    """
    Observes point cloud data from an ADAR device and publishes it to a Foxglove server.

    Args:
        args: Parsed command-line arguments containing:
            - ipaddr: IP address of the ADAR device.
            - foxglove_host: Host IP address for the Foxglove server.

    Prints:
        - Status messages indicating the number of messages published.
    """
    print("Starting CoAP observer...")
    msg_count = 0

    # Initialize the point cloud publisher
    pointcloud_publisher = PointCloudPublisher(topic=POINTCLOUD_TOPIC, auto_publish_transforms=True)

    # Create a CoAP client context
    ctx = await Context.create_client_context()

    # Initialize the ADAR device connection
    adar = Adar(ctx, args.ipaddr)

    # Observe point cloud data and publish it
    async for coap_msg in adar.observe_point_cloud():
        pointcloud_publisher.publish(coap_msg.points)
        msg_count += 1

        if msg_count % 100 == 0 or msg_count == 1:
            print(f"Published {msg_count} messages.")


def main():
    asyncio.run(async_main())
    print("All done.")


if __name__ == "__main__":
    main()
