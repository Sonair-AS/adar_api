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
import json
import sys
import os

import foxglove
from aiocoap import Context

from adar_api import Adar
from adar_api.examples.utils import (
    PointCloudPublisher,
    DeviceStatusPublisher,
    ZonePublisher,
)

# Define the topic for publishing point cloud data
POINTCLOUD_TOPIC = "/adar/pointcloud"
DEVICE_STATUS_TOPIC = "/adar/device_status"
ZONE_TOPIC = "/adar/zone"


async def async_main() -> None:
    """
    Main asynchronous entry point for the script.

    - Parses command-line arguments.
    - Initializes the Foxglove server.
    - Starts the CoAP loop to observe and publish point cloud data and device status.
    - Publishes zone data from a configuration file.

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
    parser.add_argument(
        "--config-path",
        type=str,
        default=None,
        help="Path to the ADAR device configuration file (default: None)",
    )
    args = parser.parse_args()

    # Initialize the Foxglove server
    foxglove.start_server(host=args.foxglove_host)

    # Start the CoAP loop to observe and publish point cloud data
    try:
        await coap_loop(args)
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\nShutting down gracefully...")
        return  # Exit gracefully without error
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


async def zone_publisher_task(config_path: str, zone_publisher: ZonePublisher) -> None:
    """
    Background task that publishes zone configuration every 5 seconds.
    Only reads and recalculates zones if the config file has been modified.

    Args:
        config_path: Path to the configuration file
        zone_publisher: ZonePublisher instance to use for publishing
    """

    print("Starting zone publisher background task...")

    last_mtime = None
    has_zones = False

    while True:
        try:
            # Check if file has been modified
            current_mtime = os.path.getmtime(config_path)

            if last_mtime != current_mtime:
                # File changed, read, parse, and update zones
                with open(config_path, "r") as f:
                    config = json.load(f)
                zone_publisher.update_zones(config)
                last_mtime = current_mtime
                has_zones = True
                active_zone = zone_publisher.get_active_zone()
                print(f"Zone configuration updated. Active zone ID: {active_zone}")

            # Publish cached markers every cycle
            if has_zones:
                zone_publisher.publish()

        except FileNotFoundError:
            print(f"Warning: Config file not found: {config_path}", file=sys.stderr)
            has_zones = False
            last_mtime = None
        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse config file: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Warning: Error publishing zones: {e}", file=sys.stderr)

        # Wait 5 seconds before next publish
        await asyncio.sleep(5)


async def coap_loop(args) -> None:
    """
    Observes point cloud data from an ADAR device and publishes it to a Foxglove server.

    Args:
        args: Parsed command-line arguments containing:
            - ipaddr: IP address of the ADAR device.
            - foxglove_host: Host IP address for the Foxglove server.
            - config_path: Path to the ADAR device configuration file.
    Prints:
        - Status messages indicating the number of messages published.
    """
    print("Starting CoAP observer...")
    msg_count = 0

    # Initialize the point cloud publisher
    pointcloud_publisher = PointCloudPublisher(topic=POINTCLOUD_TOPIC, auto_publish_transforms=True)
    device_status_publisher = DeviceStatusPublisher(topic=DEVICE_STATUS_TOPIC)
    # Start zone publisher background task if config is provided
    zone_publisher = None
    if args.config_path:
        zone_publisher = ZonePublisher(topic=ZONE_TOPIC)
        # Create background task to publish zones every 5 seconds
        _zone_task = asyncio.create_task(zone_publisher_task(args.config_path, zone_publisher))

    # Create a CoAP client context
    ctx = await Context.create_client_context()

    try:
        # Initialize the ADAR device connection
        adar = Adar(ctx, args.ipaddr)

        print(f"Connected to ADAR device at {args.ipaddr}")

        while True:
            try:
                # Observe point cloud data and publish it
                async for coap_msg in adar.observe_point_cloud():
                    try:
                        pointcloud_publisher.publish(coap_msg.points, coap_msg.timestamp)
                        device_status_publisher.publish(coap_msg.status)
                        msg_count += 1

                        # Update active zone if it changed
                        if zone_publisher:
                            zone_changed = zone_publisher.set_active_zone(coap_msg.status.zone_selected)
                            if zone_changed:
                                print(f"Active zone changed to: {coap_msg.status.zone_selected}")

                        if msg_count % 100 == 0 or msg_count == 1:
                            print(f"Published {msg_count} messages.")

                    except Exception as e:
                        print(f"Warning: Error processing message: {e}", file=sys.stderr)
                        continue

            except KeyboardInterrupt:
                print("\nReceived interrupt signal...")
                raise

            except asyncio.CancelledError:
                # Task was cancelled (usually during shutdown)
                print("Task cancelled, shutting down...")
                raise

            except Exception as e:
                # Connection error - wait a bit and retry
                print(f"Error: {e}. Retrying in 0.5 seconds...", file=sys.stderr)
                await asyncio.sleep(0.5)

    finally:
        # Clean up CoAP context
        print("Cleaning up...")
        await ctx.shutdown()


def main():
    asyncio.run(async_main())
    print("All done.")


if __name__ == "__main__":
    main()
