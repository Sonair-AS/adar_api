# ADAR API Python Package

A Python package for communicating with the ADAR 3D Ultrasonic Sensor via Constrained Application Protocol (CoAP).

## Overview

This package serves two main purposes:

1. **Easy-to-use Python API**: Provides a simple interface for receiving 3D point cloud data from ADAR sensors, for conversion to other ecosystems like ROS or Foxglove.

2. **Reference Implementation**: Documents the CoAP resources and binary data formats to enable porting to other languages (C, C++, etc.)

## Table of Contents

- [Installation](#installation)
- [Network Requirements](#network-requirements)
- [Quick Start](#quick-start)
  - [Point Cloud Publisher](#point-cloud-publisher)
  - [ROS Integration](#ros-integration)
  - [ADAR API](#adar-api)
- [API Reference](#api-reference) - _For Python developers_
  - [Error Handling](#error-handling)
  - [Usage Examples](#usage-examples)
- [CoAP Resources and Data Formats](#coap-resources-and-data-formats) - _For protocol reference_

## Installation

> **Compatibility:** ADAR API v2.0.0-rc is a breaking change and requires **firmware 1.8.3 or newer**. It is not backwards-compatible with firmware 1.1.x. If you are running firmware 1.1.1 or older, see [From PyPI](#from-pypi-firmware-111-or-older) below.

**Prerequisites:** [Python 3.11+](https://www.python.org/downloads/) and [Git](https://git-scm.com/downloads) must be installed.

### From Git (firmware 1.8.3 or newer)

Install from the Git repository:

1. **Clone the repository and check out the correct branch:**

   ```bash
   git clone -b <branch> https://github.com/Sonair-AS/adar_api.git
   cd adar_api
   ```

   > Replace `<branch>` with the branch name provided in the release notes (e.g. `v2.0.0-rc`).

2. **Create and activate a virtual environment:**

   ```bash
   python -m venv .venv
   ```

   Then activate it:

   **Linux/macOS:**

   ```bash
   source .venv/bin/activate
   ```

   **Windows (cmd):**

   ```cmd
   .venv\Scripts\activate
   ```

   **Windows (PowerShell):**

   ```PowerShell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process -Force
   .venv\Scripts\Activate.ps1
   ```

3. **Install the package:**

   ```bash
   pip install .
   ```

4. **Verify the installation:**

   ```bash
   python -c "from adar_api import Adar; print('adar_api installed successfully')"
   ```

#### Updating to a newer release

When a new release or version is available, update your local clone:

```bash
cd adar_api
git fetch
git pull
pip install .
```

### From PyPI (firmware 1.1.1 or older)

For firmware version 1.1.1 or older, install from PyPI:

```bash
pip install adar-api
```

> **Note:** The PyPI version (1.x) is only compatible with firmware 1.1.1 or older. If you have firmware 1.8.3 or newer, you must use the [Git installation](#from-git-firmware-183-or-newer) method above.

**Note:** You need to activate the virtual environment each time you want to use the `pointcloud-publisher` command or the ADAR API in a new terminal session. To deactivate the virtual environment, simply type `deactivate`.

## Network Requirements

- **Protocol**: CoAP over UDP (port 5683)
- **Network**: IPv4 connectivity to sensor
- **Firewall**: Ensure UDP port 5683 is accessible

## Quick Start

### Point cloud Publisher

The easiest way to visualize the ADAR point cloud is to use the built-in `pointcloud-publisher`:

```bash
pointcloud-publisher <ADAR_IP_ADDRESS>
```

Example for an ADAR with factory-default IP address:

```bash
pointcloud-publisher 10.20.30.40
```

#### Advanced Usage

Specify a custom Foxglove server host:
This can be useful if you want to publish the pointcloud to a different computer than the one running the pointcloud-publisher script.

```bash
pointcloud-publisher <ADAR_IP_ADDRESS> --foxglove-host <HOST_IP>
```

Example for broadcasting to a specific foxglove host:
This will publish the pointcloud from an ADAR with IP address `10.20.30.40` to a foxglove host running on IP address 127.0.0.2

```bash
pointcloud-publisher 10.20.30.40 --foxglove-host 127.0.0.2
```

Example for zone visualization:
This will publish the active zone presets as markers in Foxglove. The zones are read from an ADAR configuration file and automatically switch based on the device's active zone.

```bash
pointcloud-publisher 10.20.30.40 --config-path path/to/config.adar
```

**Command Line Options:**

- `ipaddr` (required): IP address of the ADAR device
- `--foxglove-host` (optional): Host IP address for the Foxglove server (default: 127.0.0.1)
- `--config-path` (optional): Path to the ADAR device configuration file for zone visualization (default: None)

#### Visualization with Foxglove Studio

1. **Start the pointcloud publisher** (as shown above)
2. **Open Foxglove Studio**
3. **Connect to the Foxglove server:**
   - Go to "Open connection"
   - Select "Foxglove WebSocket"
   - Enter `ws://127.0.0.1:8765` (or your custom host)
4. **Import layout for ADAR:**
   - In the top right pane, select the layout drop-down and click "Import from file..."
   - Select the [`foxglove_layout_ADAR.json`](adar_api/examples/foxglove_layout_ADAR.json) file.
   - The point cloud should now appear in a 3D view and a 2D top-down view.

### ROS Integration

For ROS (Robot Operating System) integration, see the [ROS example documentation](adar_api/examples/ros/sonair_adar/README.md) for detailed setup instructions, including Docker configuration and usage examples.

### ADAR API

For custom integrations, use the Python API directly:

```python
import asyncio
from adar_api import Adar, CoapPointCloud
from aiocoap import Context

async def main():
    # Create CoAP context
    ctx = await Context.create_client_context()

    # Connect to ADAR sensor
    adar = Adar(ctx, ip_address="10.20.30.40")

    # Get device information
    device_info = await adar.get_device_info()
    print(f"Device: {device_info.device_name}")
    print(f"Firmware: {device_info.firmware_version}")

    # Get single point cloud frame
    point_cloud: CoapPointCloud = await adar.get_point_cloud()
    print(f"Received {len(point_cloud.points)} points")

    # Continuous observation
    async for point_cloud in adar.observe_point_cloud():
        print(f"Received {len(point_cloud.points)} points")
        for point in point_cloud.points:
            print(f"Point: x={point.x:.3f}m, y={point.y:.3f}m, z={point.z:.3f}m, "
                  f"strength={point.strength}, classification={point.classification}")

if __name__ == "__main__":
    asyncio.run(main())
```

## API Reference

### Error Handling

The API provides structured exception handling:

```python
from adar_api import CoapException, CoapErrorException

try:
    point_cloud = await adar.get_point_cloud()
except CoapErrorException as e:
    print(f"CoAP protocol error: {e.response.code}")
except CoapException as e:
    print(f"General CoAP error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

### Response Code Handling

CoAP errors include response codes that indicate the type of failure or success.

For a complete list of response codes, see [CoAP Response Codes](#coap-response-codes) in the protocol reference.

### Usage Examples

#### Robust Point Cloud Observation

```python
async def robust_observation():
    async for point_cloud in adar.observe_point_cloud(keep_running=True):
        try:
            # Process point cloud
            # Use to_thread to avoid blocking the underlying async network io task,
            # which could cause network buffer overflow if process_points takes too long.
            await asyncio.to_thread(process_points, point_cloud.points)
        except Exception as e:
            logger.warning(f"Processing error: {e}")
            # Continue observation despite processing errors
```

#### Direct CoAP Request

```python
from aiocoap import Message, GET

# Access the underlying CoAP request method
response = await adar.send_request(
    Message(code=GET, uri=f"coap://{adar.ip_address}/status/v1")
)
```

#### Network Configuration

```python
from adar_api import NetworkConfig

# Get current configuration
config = await adar.get_network_config()
print(f"DHCP: {config.dhcp_enabled}")
print(f"Static IP: {config.static_ip}")
print(f"Device Tag: {config.device_tag}")

# To change the network configuration, create a new NetworkConfig with the desired parameters.
# Note: modifying attributes on an existing NetworkConfig does not update the underlying binary
# data. Always construct a new NetworkConfig when writing changes.
new_config = NetworkConfig(
    dhcp_enabled=False,
    static_ip="10.20.30.50",
    subnet_mask="255.255.255.0",
    gateway="10.20.30.1",
    device_tag="my-sensor",
)

# Apply configuration (requires login, device will reboot)
await adar.login(password="your_password")
await adar.set_network_config(new_config)
```

#### Transmission Code Configuration

```python
# Get current transmission code
code_id = await adar.get_transmission_code_id()
print(f"Current transmission code: {code_id}")

# Set transmission code ID (valid values: 1, 2, 4, 8)
await adar.set_transmission_code_id(4)
```

> **Note:** The Python API uses **code IDs** (1, 2, 4, 8), while the CoAP protocol uses **code indices** (0, 1, 2, 3). The relationship is: code ID = 2^index. The Python API handles this conversion automatically.

## CoAP Resources and Data Formats

For developers integrating towards ADAR using other languages, this section documents the CoAP API resources and data formats.

### Resource URI Structure

```
coap://<device_ip>/<resource>/<version>
```

### Resource Reference

| Resource                | Method      | Description             | Response Format                                 |
| ----------------------- | ----------- | ----------------------- | ----------------------------------------------- |
| `/pointcloud/v1`        | GET/OBSERVE | 3D point cloud data     | [Point Cloud Format](#point-cloud-format)       |
| `/status/v1`            | GET         | Device status           | [Device Status Format](#device-status-format)   |
| `/device_info/v1`       | GET         | Device identification   | [Device Info Format](#device-info-format)       |
| `/network_config/v1`    | GET/PUT     | Network configuration   | [Network Config Format](#network-config-format) |
| `/config/crc/v1`        | GET         | Configuration CRC       | 4 bytes, uint32, little-endian                  |
| `/errors/v1`            | GET         | Device error codes      | [Error Format](#error-format)                   |
| `/transmission_code/v1` | GET/PUT     | Transmission code index | Single byte. Legal values: 0, 1, 2, 3           |
| `/login/v1`             | GET/PUT     | Authentication          | GET: login token; PUT: auth token               |
| `/logout/v1`            | PUT         | End session             | Empty payload                                   |
| `/state/v1`             | PUT         | Set device state        | Single byte (3=Enabled, 4=Disabled, 5=Config)   |
| `/factory_reset/v1`     | PUT         | Factory reset           | Empty payload                                   |
| `/reboot/v1`            | PUT         | Reboot device           | Empty payload                                   |
| `/observers/v1`         | DELETE      | Clear all observers     | Empty payload                                   |

> **Note:** Legacy v0 endpoints are still available for backwards compatibility but may be removed in a future release. New integrations should use the versions listed above.

### Data Format Specifications (little-endian)

#### Point Cloud Format

Binary payload structure:

| Byte Range | Field         | Type               | Description                                       |
| ---------- | ------------- | ------------------ | ------------------------------------------------- |
| 0-7        | Timestamp     | uint64             | Microseconds since measurement start              |
| 8-15       | Device Status | 8 bytes            | See [Device Status Format](#device-status-format) |
| 16+        | Point Data    | 10 bytes per point | See [Point Format](#point-format)                 |

_Note: The number of points is determined by parsing 10-byte chunks until the payload ends. The total payload length minus the 16-byte header must be divisible by 10, or the data is considered corrupted._

##### Point Format

| Byte Range | Field          | Type   | Description                                       |
| ---------- | -------------- | ------ | ------------------------------------------------- |
| 0-1        | X coordinate   | int16  | Millimeters, signed                               |
| 2-3        | Y coordinate   | int16  | Millimeters, signed                               |
| 4-5        | Z coordinate   | int16  | Millimeters, signed                               |
| 6-7        | Strength       | uint16 | Signal strength, unsigned                         |
| 8          | Reserved       | uint8  | Ignore                                            |
| 9          | Classification | uint8  | See [Classification Flags](#classification-flags) |

_Note: The Python API converts coordinates from millimeters to meters._

##### Classification Flags

| Bit 7-4  | Bit 3                   | Bit 2                       | Bit 1                       | Bit 0                    |
| -------- | ----------------------- | --------------------------- | --------------------------- | ------------------------ |
| Reserved | Point in Exclusion Zone | Point in Outer Warning Zone | Point in Inner Warning Zone | Point in Protective Zone |

#### Device Status Format

8-byte binary structure:

| Byte Range | Field             | Type   | Description                                            |
| ---------- | ----------------- | ------ | ------------------------------------------------------ |
| 0          | Zone Selected     | uint8  | Currently selected zone                                |
| 1          | Device State      | uint8  | See [Device States](#device-states)                    |
| 2          | Transmission Code | uint8  | Transmission code index (0-3, where code ID = 2^index) |
| 3          | Zone Status       | uint8  | See [Zone Status Flags](#zone-status-flags)            |
| 4-7        | Device Error      | uint32 | Error code, little-endian                              |

##### Device States

- 1: Init
- 2: SelfTest
- 3: Enabled
- 4: Disabled
- 5: Config
- 6: Error
- 7: Fault

##### Zone Status Flags

| Bit 7-3  | Bit 2                        | Bit 1                        | Bit 0                     |
| -------- | ---------------------------- | ---------------------------- | ------------------------- |
| Reserved | Object in Outer Warning Zone | Object in Inner Warning Zone | Object in Protective Zone |

#### Device Info Format

Variable-length format with [length-prefixed strings](#length-prefixed-string-format):

| Byte Range   | Field                   | Type            | Description                                      |
| ------------ | ----------------------- | --------------- | ------------------------------------------------ |
| 0-3          | Serial Number           | uint32          | Device serial number, little-endian              |
| 4-6          | Hardware Version        | 3 Bytes (uint8) | Hardware version bytes (major.minor.patch)       |
| 7-10         | Product Number Length   | uint32          | Length of product number string, little-endian   |
| 11+          | Product Number          | UTF-8 string    | Product number string                            |
| Next 4 bytes | Device Name Length      | uint32          | Length of device name string, little-endian      |
| Next N bytes | Device Name             | UTF-8 string    | Device name string                               |
| Next 4 bytes | Firmware Version Length | uint32          | Length of firmware version string, little-endian |
| Next N bytes | Firmware Version        | UTF-8 string    | Firmware version string                          |

##### Length-prefixed String Format

- 4 bytes: String length (uint32, little-endian)
- N bytes: UTF-8 string data

#### Network Config Format

212-byte binary structure:

| Byte Range | Field               | Type              | Description                                                          |
| ---------- | ------------------- | ----------------- | -------------------------------------------------------------------- |
| 0-3        | Configuration Flags | uint32            | See [Configuration Flags](#configuration-flags)                      |
| 4-7        | Static IP Address   | 4 Bytes (uint8)   | Static IP address bytes                                              |
| 8-11       | Subnet Mask         | 4 Bytes (uint8)   | Subnet mask bytes                                                    |
| 12-15      | Gateway Address     | 4 Bytes (uint8)   | Gateway IP address bytes                                             |
| 16-19      | Sync Server IP      | 4 Bytes (uint8)   | Synchronization server IP address                                    |
| 20-83      | Reserved            | 64 Bytes (uint8)  | Reserved bytes                                                       |
| 84-211     | Device Tag          | 128 Bytes (uint8) | Reserved for Device Tag. Should be set to existing value or all-zero |

##### Configuration Flags

| Bit 31-3 | Bit 2            | Bit 1        | Bit 0                                |
| -------- | ---------------- | ------------ | ------------------------------------ |
| Reserved | Sync server mode | Sync enabled | Static IP enabled (0=DHCP, 1=Static) |

#### Error Format

Variable-length format with error bitmask and description strings:

| Byte Range | Field                   | Type     | Description                                     |
| ---------- | ----------------------- | -------- | ----------------------------------------------- |
| 0-3        | Error Bitmask           | uint32   | Error bitmask, little-endian                    |
| 4-7        | Number of Error Strings | uint32   | Count of error strings, little-endian           |
| 8+         | Error Strings           | Variable | See [Error String Format](#error-string-format) |

##### Error String Format

- 4 bytes: String length (uint32, little-endian)
- N bytes: UTF-8 error description

#### Transmission Code Format

Single byte payload:

| Byte | Field      | Type  | Description                             |
| ---- | ---------- | ----- | --------------------------------------- |
| 0    | Code index | uint8 | Transmission code Index (0, 1, 2, or 3) |

### CoAP Response Codes

When working with ADAR resources, you may encounter these CoAP response codes:

#### Success Responses

- **`2.02 Deleted`** - Resource successfully deleted
- **`2.04 Changed`** - Resource successfully modified (PUT operations)
- **`2.05 Content`** - Resource successfully retrieved (GET operations)

#### Client Error Responses

- **`4.00 Bad Request`** - Malformed request or invalid payload data
- **`4.04 Not Found`** - Resource does not exist (e.g., typos in resource paths like `/pointclouds/v1` instead of `/pointcloud/v1`) or unauthorized access
- **`4.05 Method Not Allowed`** - Invalid HTTP method for the resource (e.g., PUT to a read-only resource)
- **`4.08 Request Entity Incomplete`** - Missing or incomplete payload for operations that require data
- **`4.29 Too Many Requests`** - Observer limit exceeded (max 2 point cloud observers)

#### Server Error Responses

- **`5.01 Not Implemented`** - Resource is deprecated or not supported in the current firmware version
