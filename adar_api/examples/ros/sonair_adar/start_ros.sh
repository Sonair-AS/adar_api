#!/bin/bash
set -eo pipefail  # remove 'u'

# Source ROS environment
source /opt/ros/jazzy/setup.sh
source /adar_api/ros/install/local_setup.sh

# Check DEVICE_IP
if [ -z "${DEVICE_IP:-}" ]; then
  echo "Error: DEVICE_IP environment variable must be set"
  exit 1
fi

# Launch node
exec ros2 launch sonair_adar sonair_adar.launch.py device_ip:=${DEVICE_IP}