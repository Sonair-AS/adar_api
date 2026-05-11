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

> **Compatibility:** ADAR API 2.0 supports both v0 and v1 endpoints. The package automatically detects the endpoint version supported by the device. Features requiring authentication (login, state control, reboot) are only available on v1 endpoints.

**Prerequisites:** [Python 3.11+](https://www.python.org/downloads/) must be installed.

### Quick Installation

Install the ADAR API package from PyPI:

```bash
pip install adar-api
```

### Recommended: Using a Virtual Environment

For better dependency management, it's recommended to use a virtual environment:

1. **Create a virtual environment:**

   ```bash
   python -m venv .venv
   ```

2. **Activate the virtual environment:**

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
   pip install adar-api
   ```

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
    print(f"Serial: {device_info.device_identification.serial_number}")
    print(f"Hardware: {device_info.device_identification.hardware_version}")

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

Resources that do not require authentication:

| Resource                | Method        | Description              | Response Format                                 |
| ----------------------- | -----------   | -----------------------  | ----------------------------------------------- |
| `/pointcloud/v1`        | GET (Observe) | 3D point cloud data      | [Point Cloud Format](#point-cloud-format)       |
| `/status/v1`            | GET           | Device status            | [Device Status Format](#device-status-format)   |
| `/device_info/v1`       | GET           | Device identification    | [Device Info Format](#device-info-format)       |
| `/network_config/v1`    | GET           | Network configuration    | [Network Config Format](#network-config-format) |
| `/errors/v1`            | GET           | Device error codes       | [Error Format](#error-format)                   |
| `/transmission_code/v1` | GET/PUT       | Transmission code index  | Single byte (0, 1, 2, or 3)                     |
| `/protocol_hash/v1`     | GET           | Protocol version hash    | 4 bytes, uint32, little-endian                  |
| `/state/v1`             | GET           | Current device state     | Single byte (see state values below)            |
| `/login/v1`             | GET           | Login challenge token    | 8 bytes, uint64, little-endian                  |
| `/observers/v1`         | DELETE        | Clear all observers      | Empty payload                                   |
| `/logout/v1`            | PUT           | End session              | Empty payload                                   |
| `/login/v1`             | PUT           | Submit login credentials | See [Authentication](#authentication)           |

Resources that require authentication (see [Authentication](#authentication)):

| Resource                | Method      | Required [State(s)](#device-states) | Description                        | Payload / Response Format                       |
| ----------------------- | ----------- | ----------------------------------- | ---------------------------------- | ----------------------------------------------- |
| `/state/v1`             | PUT         | Enabled, Disabled, Error, SelfTest  | Set device state                   | Single byte (3=Enabled, 4=Disabled)             |
| `/network_config/v1`    | PUT         | Disabled                            | Update network configuration       | [Network Config Format](#network-config-format) |
| `/firmware/v1`          | PUT         | Disabled, Fault                     | Upload firmware image              | Binary firmware image                           |
| `/factory_reset/v1`     | POST        | Disabled                            | Factory reset                      | Empty payload                                   |
| `/reboot/v1`            | PUT         | Any                                 | Reboot device                      | Empty payload                                   |

> **Note:** Legacy v0 endpoints are deprecated and will return `5.01 Not Implemented`.

### Payload CRC

Every CoAP message that carries a non-empty payload, in both directions, includes a **CRC-32** checksum as the last 4 bytes. This applies to all resource paths and all methods (GET responses, OBSERVE notifications, PUT requests, etc.).
The CRC covers both the **resource path** and the **payload data**, in that order.

Messages with an empty payload (e.g., a GET request or a PUT to `/reboot/v1`) do not carry a CRC.

The device will respond with **4.00 Bad Request** if a received message has an invalid or missing CRC.

> **Note:** CRC was introduced together with the v1 resource paths. Older firmware with only v0 paths (e.g., `pointcloud/v0`) will accept messages with or without a trailing CRC, but will not include a CRC in its responses.
> Clients that need to support both old and new firmware can use the endpoint version as an indicator: v0 paths -> no CRC in responses, v1+ paths -> CRC always present.

#### CRC Calculation

The CRC-32 is computed over:

1. The **URI path** encoded as UTF-8, without leading or trailing slashes (e.g., `pointcloud/v1`)
2. The **payload bytes** (excluding the CRC itself)

The CRC algorithm is **CRC-32** (polynomial `0x04C11DB7`, also known as CRC-32/ISO-HDLC). The resulting 4-byte checksum is stored in **little-endian** byte order.

#### Receiving (GET responses, OBSERVE notifications)

When the device sends a response with a payload, the last 4 bytes are the CRC:

```
[ payload_data (N bytes) ] [ crc32 (4 bytes, little-endian) ]
```

To verify and decode:
1. Split the raw payload into `data` (all bytes except the last 4) and `crc_bytes` (the last 4 bytes)
2. Compute CRC-32 over the concatenation of the URI path bytes and `data`
3. Compare with the received CRC (interpret `crc_bytes` as a little-endian uint32)
4. If the CRC matches, parse `data` according to the resource's data format
5. If the CRC does not match, treat it as a communication error

#### Sending (PUT requests)

When sending a PUT request with a payload, append the CRC as the last 4 bytes:

1. Encode the payload `data` according to the resource's data format
2. Compute CRC-32 over the concatenation of the URI path bytes and `data`
3. Encode the CRC as 4 bytes in little-endian byte order and append them to `data`

#### Example

For a GET response on `status/v1` with 8 bytes of device status data (`00 03 00 00 00 00 00 00`):

```
CRC input:  "status/v1" (as UTF-8) ++ 00 03 00 00 00 00 00 00
CRC output: 0xEF0EE5D0
Wire payload: [ 00 03 00 00 00 00 00 00 ] [ D0 E5 0E EF ]
                                            ^^ little-endian CRC
```

This can be used as a test vector when implementing CRC validation.

### Data Format Specifications (little-endian)

#### Point Cloud Format

The point cloud resource uses [CoAP Observe](https://datatracker.ietf.org/doc/html/rfc7641). A GET with the Observe Register option registers the client as an observer and starts continuous notifications. A GET without the Observe Register option deregisters the client and does **not** return a point cloud frame. The maximum number of concurrent observers is 2; additional attempts receive `4.29 Too Many Requests`.

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

| Bit 7-5  | Bit 4          | Bit 3                   | Bit 2                       | Bit 1                       | Bit 0                    |
| -------- | -------------- | ----------------------- | --------------------------- | --------------------------- | ------------------------ |
| Reserved | Not Classified | Point in Exclusion Zone | Point in Outer Warning Zone | Point in Inner Warning Zone | Point in Protective Zone |

_Note: Bit 4 (`Not Classified`) is set when no zone preset is configured on the device. When set, bits 0-3 are all zero._

#### Device Status Format

8-byte binary structure:

| Byte Range | Field             | Type   | Description                                                                     |
| ---------- | ----------------- | ------ | ------------------------------------------------------------------------------- |
| 0          | Zone Selected     | uint8  | Currently selected zone                                                         |
| 1          | Device State      | uint8  | See [Device States](#device-states)                                             |
| 2          | Transmission Code | uint8  | Transmission code index (0-3, where code ID = 2^index)                          |
| 3          | Zone Status       | uint8  | See [Zone Status Flags](#zone-status-flags)                                     |
| 4-7        | Device Error      | uint32 | Error bitmask, little-endian. See [Device Error Bitmask](#device-error-bitmask) |

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

##### Device Error Bitmask

The `Device Error` field (uint32, little-endian) is a bitmask where each bit indicates a specific error condition. When the device state is Error or Fault, this field provides details about the cause. Multiple bits may be set simultaneously.

| Bit | Description                                                    |
| --- | -------------------------------------------------------------- |
| 0   | Zone select input doesn't match a zone ID in the active config |
| 1   | Zone select input invalid for the active encoding scheme       |
| 2   | No pulsing detected on zone select input                       |
| 3   | Error during signal processing                                 |
| 4   | Sensor error                                                   |
| 5   | Sensor error                                                   |
| 6   | Excessive ultrasound noise detected                            |
| 7   | Synchronization between sensors failed                         |
| 8   | Timeout during signal processing                               |
| 9   | The sensor is obstructed                                       |
| 10  | Service needed                                                 |
| 11  | OSSD0 pulse test verification failed                           |
| 12  | OSSD1 pulse test verification failed                           |
| 13  | Object in protective zone possibly unaccounted for             |
| 14  | Zone select input is unstable                                  |
| 15  | Zone select input validation failure                           |
| 16  | CPU 1 in undefined state                                       |
| 17  | CPU 2 in undefined state                                       |
| 18  | Unsupported hardware version                                   |
| 19  | OSSD0 off-state (low) check failed                             |
| 20  | OSSD1 off-state (low) check failed                             |

Bits 21-31 are reserved.

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

| Bit 31-4 | Bit 3                     | Bit 2       | Bit 1        | Bit 0                                |
| -------- | ------------------------- | ----------- | ------------ | ------------------------------------ |
| Reserved | Sync source IP filter set | Sync source | Sync enabled | Static IP enabled (0=DHCP, 1=Static) |

_Note: When **bit 2** (Sync source) is set, this device provides the sync signal for other devices. When **bit 3** is set, the device only accepts synchronization from the IP specified in the Sync Server IP field (bytes 16-19)._

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

### Authentication

Several resources require the client to be logged in. The authentication flow uses a challenge-response mechanism:

1. **GET `/login/v1`** — The device returns an 8-byte login token (uint64, little-endian). This token is a one-time challenge.
2. The client encodes the device password using the received token.
3. **PUT `/login/v1`** — The client sends the encoded password. On success, the device responds with a session token ([length-prefixed UTF-8 string](#length-prefixed-string-format), up to 16 characters).
4. Subsequent authenticated requests include the session token as a URI query parameter: `?t=<session_token>`.

The session ends when the client sends **PUT `/logout/v1`**, or when the device is rebooted.

> **Note:** Only one user session is active at a time. A login attempt while another session is active will be rejected with **4.03 Forbidden**. The existing session must be ended (via logout or device reboot) before a new login can succeed.

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
