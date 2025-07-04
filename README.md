# ADAR API Python Package

A Python package for communicating with the ADAR 3D Ultrasonic Sensor via Constrained Application Protocol (CoAP)).

## Overview

This package serves two main purposes:

1. **Easy-to-use Python API**: Provides a simple interface for receiving 3D point cloud data from ADAR sensors, for conversion to other ecosystems like ROS or Foxglove.

2. **Reference Implementation**: Documents the CoAP resources and binary data formats to enable porting to other languages (C, C++, etc.)

## Table of Contents

- [Installation](#installation)
- [Network Requirements](#network-requirements)
- [Quick Start](#quick-start)
- [API Reference](#api-reference) - _For Python developers_
- [Coordinate System](#coordinate-system)
- [Error Handling](#error-handling)
- [Advanced Usage](#advanced-usage)
- [CoAP Resources and Data Formats](#coap-resources-and-data-formats) - _For protocol reference_

## Installation

1. Download the latest version from [Releases](https://github.com/Sonair-AS/adar_api/releases). The file should have a name similar to: `adar_api-1.0.0-py3-none-any.whl`.
2. Open a terminal window and navigate to the folder containing the downloaded file (e.g `cd ~/downloads`)
3. Install using pip (replace the filename with the file that was downloaded in step 1)
   ```bash
   pip install <FILENAME>.whl
   ```

## Network Requirements

- **Protocol**: CoAP over UDP (port 5683)
- **Network**: IPv4 connectivity to sensor
- **Firewall**: Ensure UDP port 5683 is accessible

## Quick Start

```python
import asyncio
from adar_api import Adar
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
    point_cloud = await adar.get_point_cloud()
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
            process_points(point_cloud.points)
        except Exception as e:
            logger.warning(f"Processing error: {e}")
            # Continue observation despite processing errors
```

#### Direct CoAP Request

```python
from aiocoap import Message, GET

# Access the underlying CoAP request method
response = await adar.send_request(
    Message(code=GET, uri=f"coap://{adar.ip_address}/status/v0")
)
```

#### Network Configuration

```python
# Get current configuration
config = await adar.get_network_config()
print(f"Current DHCP setting: {config.dhcp_enabled}")

# Modify network config
config.dhcp_enabled = True

# Apply modified configuration (device will reboot and might be on a different network than before)
await adar.set_network_config(config)
```

#### Transmission Code Configuration

```python
# Get current transmission code
code_id = await adar.get_transmission_code_id()
print(f"Current transmission code: {code_id}")

# Set transmission code (valid values: 1, 2, 4, 8)
await adar.set_transmission_code_id(4)
```

## CoAP Resources and Data Formats

For developers integrating towards ADAR using other languages, this section documents the CoAP API resources and data formats.

### Resource URI Structure

```
coap://<device_ip>/<resource>/<version>
```

### Resource Reference

| Resource                | Method      | Description            | Response Format                                 |
| ----------------------- | ----------- | ---------------------- | ----------------------------------------------- |
| `/pointcloud/v0`        | GET/OBSERVE | 3D point cloud data    | [Point Cloud Format](#point-cloud-format)       |
| `/status/v0`            | GET         | Device status          | [Device Status Format](#device-status-format)   |
| `/device_info/v0`       | GET         | Device identification  | [Device Info Format](#device-info-format)       |
| `/network_config/v0`    | GET/PUT     | Network configuration  | [Network Config Format](#network-config-format) |
| `/statistics/v0`        | GET         | Operational statistics | [Statistics Format](#statistics-format)         |
| `/errors/v0`            | GET         | Device error codes     | [Error Format](#error-format)                   |
| `/transmission_code/v0` | GET/PUT     | Transmission code ID   | Single byte. Legal values: 1, 2, 4, 8           |
| `/factory_reset/v0`     | PUT         | Factory reset          | Empty payload                                   |
| `/observers/v0`         | DELETE      | Clear all observers    | Empty payload                                   |

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

_Note: This format uses a transmission code index (0-3), while the [Transmission Code](#transmission-code-format) resource uses a code ID (1, 2, 4, 8)._

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

#### Statistics Format

44-byte binary structure:

| Byte Range | Field                                   | Type                                | Description                                  |
| ---------- | --------------------------------------- | ----------------------------------- | -------------------------------------------- |
| 0-11       | Uptime                                  | [Duration format](#duration-format) | Device uptime                                |
| 12-19      | Total Number of Pings                   | uint64                              | Total pings count, little-endian             |
| 20-27      | Pings with Object in Protective Zone    | uint64                              | Protective zone detections, little-endian    |
| 28-35      | Pings with Object in Inner Warning Zone | uint64                              | Inner warning zone detections, little-endian |
| 36-43      | Pings with Object in Outer Warning Zone | uint64                              | Outer warning zone detections, little-endian |

##### Duration Format

| Byte Range | Field       | Type   | Description                          |
| ---------- | ----------- | ------ | ------------------------------------ |
| 0-7        | Seconds     | uint64 | Seconds component, little-endian     |
| 8-11       | Nanoseconds | uint32 | Nanoseconds component, little-endian |

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

| Byte | Field   | Type  | Description                          |
| ---- | ------- | ----- | ------------------------------------ |
| 0    | Code ID | uint8 | Transmission code ID (1, 2, 4, or 8) |

_Note: This resource uses the code ID (which is a binary bitmask), while the [Device Status](#device-status-format) uses a transmission code index (0-3) where the code ID is 2^index._

### CoAP Response Codes

When working with ADAR resources, you may encounter these CoAP response codes:

#### Success Responses

- **`2.02 Deleted`** - Resource successfully deleted
- **`2.04 Changed`** - Resource successfully modified (PUT operations)
- **`2.05 Content`** - Resource successfully retrieved (GET operations)

#### Client Error Responses

- **`4.00 Bad Request`** - Malformed request or invalid payload data
- **`4.04 Not Found`** - Resource does not exist (e.g., typos in resource paths like `/pointclouds/v0` instead of `/pointcloud/v0`) or unauthorized access
- **`4.05 Method Not Allowed`** - Invalid HTTP method for the resource (e.g., PUT to a read-only resource)
- **`4.08 Request Entity Incomplete`** - Missing or incomplete payload for operations that require data
- **`4.29 Too Many Requests`** - Observer limit exceeded (max 2 point cloud observers)

#### Server Error Responses

- **`5.01 Not Implemented`** - Resource is deprecated or not supported in the current firmware version
