# Changelog

All notable changes to ADAR API will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and ADAR API adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
