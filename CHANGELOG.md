# Changelog

All notable changes to ADAR API will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and ADAR API adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] 2026-05-11

> **Note:** This version supports both v0 and v1 endpoints. The package automatically detects the endpoint version supported by the device. Features requiring authentication (login, state control, etc.) are only available on v1 endpoints.

### Added

- **CRC validation**: New `coap_crc` module for CRC-32 validation of CoAP messages. Payloads are now verified for data integrity on receipt. **Note for non-Python integrations:** All v1 CoAP responses now include a trailing 4-byte CRC that must be stripped before parsing. PUT request payloads must also include a CRC suffix. See `coap_crc.py` for the algorithm.
- **Authentication**: New `login()`, `logout()`, and `get_login_token()` methods for device authentication. Required for write operations (state changes, configuration, factory reset).
- **Device state control**: New `set_state()` method to transition the device between Enabled and Disabled states.
- **Device errors**: New `get_device_errors()` method and `DeviceErrors` class for retrieving and parsing device error information.
- **Reboot**: New `reboot()` method for remote device reboot.
- **Observer management**: New `delete_observers()` method to clear all active CoAP observers on the device.
- **Device tag**: `NetworkConfig` now supports a `device_tag` field for identifying individual sensors.
- **Sync configuration**: `NetworkConfig` now supports `sync_enabled` and `sync_server_enabled` flags for multi-device synchronization.

### Changed

- **CoAP resource versions**: All resources upgraded from v0 to v1. The Python package automatically detects the endpoint version and uses the correct resource paths. v0 resource constants are still exported for backwards compatibility with external scripts.
- **NetworkConfig**: Fixed encoding to produce the correct 212-byte format expected by all shipped firmware. The previous encoding was undersized and would be rejected by the device.
- **DeviceErrors**: Maximum error string length increased from 64 to 256 bytes, and maximum number of errors increased from 6 to 8. The wire format is unchanged (length-prefixed strings), but integrations with fixed-size buffers may need to be updated.
- **set_state()**: No longer raises `ValueError` for invalid states. Validation is now performed by the device, which returns `CoapErrorException` on rejection.
- **factory_reset()**: Changed from PUT to POST to match the device's expected method.
- **pointcloud-to-foxglove**: Clean up on exit after subscribing to pointcloud data.
- **README**: Updated installation instructions and corrected resource version references.

### Removed

- **Statistics**: Removed `Statistics` class, `Duration` class, and `get_statistics()` method. The `/statistics/v0` endpoint is no longer available on v1 devices.

## [1.2.0] 2025-11-13

### Added

- **ROS2 driver**: A ROS2 driver that connects to the ADAR with COAP and publishes the point cloud to ROS.
- **Zone visualization**: An option to publish the active zone presets as markers in Foxglove. The zones are read from an ADAR configuration file and automatically switch based on the device's active zone.
- **pointcloud-to-foxglove**: Robust error handling with automatic retry on connection errors and graceful handling of errors. The script now recovers automatically and includes proper cleanup on Ctrl+C shutdown.

### Changed

- **coap-observer**: Update coap observer documentation and example usage to asyncio.to_thread to avoid blocking and network buffer overflow.
- **foxglove-layout**: Sort point color based on y-value (ADAR coordinates) instead of distance from device. This change can make it easier to notice detections from the ceiling.
- **coap-pointcloud**: Update point string representation

## [1.1.3] 2025-09-04

### Added

- **pointcloud-publisher**: Add Classification and Timestamp to the point cloud in pointcloud_to_foxglove example.
- **License**: License the `adar_api` repository under the MIT license.

## [1.1.2] 2025-08-19

### Added

- **Github releases**: Releases are now published to both Pypi and github and the changelog is attached in the github release.

## [1.1.1] 2025-08-18

### Added

- **pointcloud-publisher cli tool**: New entrypoint for visualization of ADAR point cloud data with Foxglove Studio
- **virtual environment setup instructions**: Added setup guide for Windows and Linux with platform-specific activation commands

### Changed

- **Installation method**: Updated from wheel-based installation to PyPI installation (`pip install adar-api`)
- **Documentation structure**: Merged foxglove publisher example README into main README for better user experience

## [1.0.1] 2025-08-15

### Changed

- Removed adar_api from `requirements.txt` in the examples directory as installing adar_api does not work when downloading (and not cloning) the repository from git.

## [1.0.0] 2025-07-04

Initial release
