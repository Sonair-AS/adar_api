# ADAR API Examples

This directory contains an example application demonstrating how to use the ADAR API to publish point clouds to Foxglove for visualization.


The(`pointcloud_to_foxglove.py`) script is an application that:

- Connects to an ADAR device using the CoAP protocol
- Observes the point cloud resource
- Publishes the point cloud data to a Foxglove server
- Automatically publishes coordinate frame transforms for proper visualization

## Prerequisites

- Python 3.11 or higher
- An ADAR device accessible on your network
- [Foxglove Studio](https://foxglove.dev/) installed for visualization

## Installation
To run the example, create a python virtual environment and install dependencies

### Linux
```bash
# From the examples directory:
python -m venv .venv && source .venv/bin/activate && pip install -r ./requirements.txt
```

### Windows (CMD)
```cmd
# From the examples directory:
python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt
```

## Usage

Run the example with your ADAR device's IP address:

```bash
python pointcloud_to_foxglove.py <ADAR_IP_ADDRESS>
```

Example:
```bash
python pointcloud_to_foxglove.py 192.168.1.100
```

### Advanced Usage

Specify a custom Foxglove server host:

```bash
python pointcloud_to_foxglove.py <ADAR_IP_ADDRESS> --foxglove-host <HOST_IP>
```

Example for broadcasting to a specific foxglove host:
```bash
python pointcloud_to_foxglove.py 192.168.1.100 --foxglove-host 127.0.0.2
```


### Command Line Options

- `ipaddr` (required): IP address of the ADAR device
- `--foxglove-host` (optional): Host IP address for the Foxglove server (default: 127.0.0.1)

## Visualization with Foxglove Studio

1. **Start the example script** (as shown above)
2. **Open Foxglove Studio**
3. **Connect to the Foxglove server:**
   - Go to "Open connection" 
   - Select "Foxglove WebSocket"
   - Enter `ws://127.0.0.1:8765` (or your custom host)
4. **Import layout for ADAR:**
   - In the top right pane, select the layout drop-down and click "Import from file..."
   - Select `foxglove_layout_ADAR.json`
   - The point cloud should now appear in a 3D view and a 2D top-down view.

## Output

The script will output status messages showing the number of published messages:
```
Starting CoAP observer...
Published 1 messages.
Published 100 messages.
Published 200 messages.
...
```