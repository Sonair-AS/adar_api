from setuptools import find_packages, setup
import os
from glob import glob

package_name = "sonair_adar"

setup(
    name=package_name,
    version="0.0.1",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        # Include launch files
        (os.path.join("share", package_name, "launch"), glob("launch/*.py")),
    ],
    install_requires=[
        "setuptools",
        "adar_api",
        "aiocoap>=0.4.0",
        "numpy>=1.20.0",
    ],
    zip_safe=True,
    maintainer="Sonair",
    maintainer_email="support@sonair.com",
    description="ROS2 driver for ADAR",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "point_cloud_publisher = sonair_adar.point_cloud_ros_publisher:main",
        ],
    },
)
