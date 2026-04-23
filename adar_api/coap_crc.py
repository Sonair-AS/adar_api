"""CRC utilities for CoAP message validation.

This module provides functions for calculating and verifying CRC-32 checksums
on CoAP messages. The CRC is calculated over both the URI path and payload.
"""

import crcmod


def calculate_crc(uri: str, payload: bytes) -> int:
    """Calculate CRC-32 for a CoAP message.

    Args:
        uri: The URI path (e.g., "/pointcloud/v1" or "pointcloud/v1").
            Leading and trailing slashes are stripped automatically.
        payload: The message payload bytes.

    Returns:
        int: The calculated CRC-32 value.
    """
    crc32 = crcmod.predefined.Crc("crc-32")
    crc32.update(uri.strip("/").encode("utf-8"))
    crc32.update(payload)
    return crc32.crcValue


def append_crc(uri: str, payload: bytes) -> bytes:
    """Append CRC-32 to a payload.

    Args:
        uri: The URI path (e.g., "/pointcloud/v1" or "pointcloud/v1").
            Leading and trailing slashes are stripped automatically.
        payload: The message payload bytes.

    Returns:
        bytes: The payload with CRC-32 appended (4 bytes, little-endian).
    """
    crc = calculate_crc(uri, payload)
    return payload + crc.to_bytes(4, byteorder="little", signed=False)


def verify_and_strip_crc(uri: str, payload: bytes) -> tuple[bytes, bool]:
    """Verify CRC-32 and strip it from the payload.

    Args:
        uri: The URI path (e.g., "/pointcloud/v1" or "pointcloud/v1").
            Leading and trailing slashes are stripped automatically.
        payload: The message payload bytes including CRC (last 4 bytes).

    Returns:
        tuple[bytes, bool]: A tuple of (stripped_payload, crc_valid).
            - stripped_payload: The payload without the CRC bytes.
            - crc_valid: True if CRC matches, False otherwise.
    """
    if len(payload) < 4:
        return payload, False

    data = payload[:-4]
    expected_crc = int.from_bytes(payload[-4:], byteorder="little", signed=False)
    actual_crc = calculate_crc(uri, data)

    return data, expected_crc == actual_crc
