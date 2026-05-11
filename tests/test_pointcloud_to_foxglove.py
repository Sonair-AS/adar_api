"""Smoke tests for the pointcloud_to_foxglove example script.

These tests verify the example code can be imported and basic structure is correct.
The example code itself is a thin wrapper around the adar_api library, which has
its own comprehensive tests.
"""

import argparse


def test_example_can_be_imported():
    """Verify the example module can be imported without errors."""
    from adar_api.examples import pointcloud_to_foxglove

    assert pointcloud_to_foxglove is not None


def test_main_functions_exist():
    """Verify the expected entry points exist."""
    from adar_api.examples.pointcloud_to_foxglove import (
        main,
        async_main,
        coap_loop,
        zone_publisher_task,
    )

    assert callable(main)
    assert callable(async_main)
    assert callable(coap_loop)
    assert callable(zone_publisher_task)


def test_topics_are_defined():
    """Verify the Foxglove topics are defined."""
    from adar_api.examples.pointcloud_to_foxglove import (
        POINTCLOUD_TOPIC,
        DEVICE_STATUS_TOPIC,
        ZONE_TOPIC,
    )

    assert POINTCLOUD_TOPIC == "/adar/pointcloud"
    assert DEVICE_STATUS_TOPIC == "/adar/device_status"
    assert ZONE_TOPIC == "/adar/zone"


def test_argument_parser_configuration():
    """Test that command-line arguments are parsed correctly."""
    # Replicate the argument parser from the example
    parser = argparse.ArgumentParser()
    parser.add_argument("ipaddr", type=str)
    parser.add_argument("--foxglove-host", type=str, default="127.0.0.1")
    parser.add_argument("--config-path", type=str)

    # Test with minimal args
    args = parser.parse_args(["10.20.30.40"])
    assert args.ipaddr == "10.20.30.40"
    assert args.foxglove_host == "127.0.0.1"
    assert args.config_path is None

    # Test with all args
    args = parser.parse_args(
        [
            "192.168.1.1",
            "--foxglove-host",
            "0.0.0.0",
            "--config-path",
            "/path/to/config.json",
        ]
    )
    assert args.ipaddr == "192.168.1.1"
    assert args.foxglove_host == "0.0.0.0"
    assert args.config_path == "/path/to/config.json"
