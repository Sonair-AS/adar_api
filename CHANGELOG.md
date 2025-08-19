# Changelog

All notable changes to ADAR API will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and ADAR API adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
