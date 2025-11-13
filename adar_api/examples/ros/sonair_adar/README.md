# Sonair ADAR ROS 2 Package

This ROS 2 package provides a driver for the Sonair ADAR, enabling point cloud data streaming and visualization in Foxglove.

## Features

- **Real-time point cloud streaming**: Connects to ADAR via CoAP and publishes point cloud data as the standard ROS format `sensor_msgs/PointCloud2`
- **Transform publishing**: Automatically publishes static transforms to the standard ROS coordinate system

## Installation

### Prerequisites

- **ROS 2**: ROS 2 installation (see [ROS 2 Installation Guide](https://docs.ros.org/en/jazzy/Installation.html))
- **Python**: Python 3.11 or higher

### Docker

The ROS point cloud publisher can be run in a Docker container. The Dockerfile can be found at [`adar_api/examples/ros/Dockerfile.sonair-adar`](../Dockerfile.sonair-adar).

1. **Install Docker Desktop**

   Follow the official getting started guide: [www.docker.com/get-started](https://www.docker.com/get-started/)

2. **Clone the repository:**

   ```bash
   git clone git@github.com:Sonair-AS/adar_api.git
   cd adar_api
   ```

3. **Navigate to the ROS folder:**

   ```bash
   cd adar_api/examples/ros
   ```

4. **Build the Docker image:**

   ```bash
   docker build -t ros-sonair-adar -f Dockerfile.sonair-adar .
   ```

5. **Run the container:**

   ```bash
   docker run -p 5683:5683/udp -p 8765:8765 --rm -e DEVICE_IP=<ADAR_IP_ADDRESS> ros-sonair-adar
   ```

   Example for an ADAR with IP address `10.20.30.40`:

   ```bash
   docker run -p 5683:5683/udp -p 8765:8765 --rm -e DEVICE_IP=10.20.30.40 ros-sonair-adar
   ```

**Docker Command Options:**

- `-p 5683:5683/udp`: Port mapping for CoAP communication (UDP). Maps host port 5683 to container port 5683. Used to receive CoAP messages from the ADAR device.
- `-p 8765:8765`: Port mapping for Foxglove Bridge (TCP). Maps host port 8765 to container port 8765. Allows Foxglove Studio to connect and visualize point clouds.
- `--rm`: Automatically remove container when it exits. Keeps your system clean by preventing orphaned containers.
- `-e DEVICE_IP=<ADAR_IP_ADDRESS>`: Sets environment variable inside the container. Passes the ADAR device IP address to the container, which uses this to connect to the ADAR device.

### Building the Package

Build the package from source (without Docker):

1. **Clone the repository:**

   ```bash
   git clone git@github.com:Sonair-AS/adar_api.git
   cd adar_api
   ```

2. **Source the ROS 2 environment:**

   ```bash
   # Source your ROS 2 installation (replace `$ROS_DISTRO` with your ROS version)
   source /opt/ros/$ROS_DISTRO/setup.bash
   ```

   Example for ROS 2 Jazzy:

   ```bash
   source /opt/ros/jazzy/setup.bash
   ```

3. **Navigate to the ROS workspace:**

   ```bash
   cd adar_api/examples/ros
   ```

   > **Note:** The following commands will create `install/`, `log/`, and `build/` folders in this directory.

4. **Build the sonair_adar package:**

   ```bash
   colcon build --packages-select sonair_adar
   ```

5. **Source the package setup file:**

   ```bash
   source install/local_setup.bash
   ```

6. **Start the ADAR point cloud publisher:**

   ```bash
   ros2 run sonair_adar point_cloud_publisher --ros-args -p device_ip:=<ADAR_IP_ADDRESS>
   ```

   Example for an ADAR with IP address `10.20.30.40`:

   ```bash
   ros2 run sonair_adar point_cloud_publisher --ros-args -p device_ip:=10.20.30.40
   ```

   The point cloud is published to `/adar/pointcloud` in the ADAR coordinate frame (see User Manual). For visualization, the launch file at `sonair_adar/launch/sonair_adar.launch.py` launches static transforms that rotate to the standard ROS coordinate system.

   > **Note:** The launch file requires foxglove-bridge. See the [Visualization with Foxglove](#visualization-with-foxglove) section below.

## Usage

### Visualization with Foxglove

Start the point cloud node, launch transforms, and visualize the point cloud in Foxglove:

1. **Install foxglove-bridge:**

   ```bash
   sudo apt install ros-$ROS_DISTRO-foxglove-bridge
   ```

2. **Start the ADAR driver:**

   ```bash
   ros2 launch sonair_adar sonair_adar.launch.py device_ip:=<ADAR_IP_ADDRESS>
   ```

   Example for an ADAR with IP address `10.20.30.40`:

   ```bash
   ros2 launch sonair_adar sonair_adar.launch.py device_ip:=10.20.30.40
   ```

3. **Open Foxglove Studio** and connect to `ws://localhost:8765`

4. **Add a 3D panel** and subscribe to the `/adar/pointcloud` topic

### Basic Usage

To run only the point cloud publisher (without transforms or foxglove-bridge), use:

```bash
ros2 run sonair_adar point_cloud_publisher --ros-args -p device_ip:=<ADAR_IP_ADDRESS>
```

Example for an ADAR with IP address `10.20.30.40`:

```bash
ros2 run sonair_adar point_cloud_publisher --ros-args -p device_ip:=10.20.30.40
```

This publishes the point cloud to `/adar/pointcloud` in the ADAR coordinate frame.

## Point Cloud Data Format

Each point in the point cloud contains:

- **x, y, z**: 3D coordinates in meters
- **strength**: Signal strength
- **classification**: Point classification
