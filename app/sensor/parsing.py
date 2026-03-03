"""AS1100 response parsing and data extraction."""

import re
from typing import Optional, Tuple


def parse_distance_response(response: str) -> Optional[int]:
    """
    Parse distance measurement response.
    
    Handles both formats:
    - Single: g#g+aaaaaaaa (from s#g command)
    - Continuous: g#h+aaaaaaaa (from s#h command)
    where aaaaaaaa is 0.1mm value
    
    Returns: distance in 0.1 mm units, or None if parse fails or data incomplete
    """
    if not response or not response.startswith("g"):
        return None
    
    try:
        # Format: g0g+00002718 (single) or g0h+00003961 (continuous)
        # Requires at least 10 characters: g#X+NNNNNN (min 6 digits for value)
        match = re.search(r"g\d+[gh]\+(\d{6,})", response)
        if match:
            return int(match.group(1))
    except (ValueError, AttributeError):
        pass
    
    return None


def parse_signal_strength_response(response: str) -> Optional[int]:
    """
    Parse signal strength response.
    
    Expected format: g#m+bbbbb
    Returns: signal strength value, or None if parse fails
    """
    if not response or not response.startswith("g"):
        return None
    
    try:
        match = re.search(r"g\d+m\+(\d+)", response)
        if match:
            return int(match.group(1))
    except (ValueError, AttributeError):
        pass
    
    return None


def parse_temperature_response(response: str) -> Optional[float]:
    """
    Parse temperature response.
    
    Expected format: g#t+aaaaa where aaaaa is 0.1°C
    Returns: temperature in °C, or None if parse fails
    """
    if not response or not response.startswith("g"):
        return None
    
    try:
        match = re.search(r"g\d+t\+(\d+)", response)
        if match:
            value_01c = int(match.group(1))
            return value_01c / 10.0
    except (ValueError, AttributeError):
        pass
    
    return None


def parse_firmware_version(response: str) -> Optional[Tuple[str, str]]:
    """
    Parse firmware version response.
    
    Expected format: g#sv+00430121 where first 4 are measure, last 4 are interface
    Returns: (measure_fw, interface_fw) tuple, or None if parse fails
    """
    if not response or not response.startswith("g"):
        return None
    
    try:
        match = re.search(r"g\d+sv\+(\d{4})(\d{4})", response)
        if match:
            return (match.group(1), match.group(2))
    except (ValueError, AttributeError):
        pass
    
    return None


def parse_serial_number(response: str) -> Optional[str]:
    """
    Parse serial number response.
    
    Expected format: g#sn+xxxxxxxx
    Returns: serial number string, or None if parse fails
    """
    if not response or not response.startswith("g"):
        return None
    
    try:
        match = re.search(r"g\d+sn\+(\d+)", response)
        if match:
            return match.group(1)
    except (ValueError, AttributeError):
        pass
    
    return None


def parse_error_stack(response: str) -> Optional[list]:
    """
    Parse error stack response.
    
    Expected format: g#re+200+211+255+...
    Returns: list of error codes, or None if parse fails
    """
    if not response or not response.startswith("g"):
        return None
    
    try:
        match = re.search(r"g\d+re\+([\d+]*)", response)
        if match:
            codes_str = match.group(1)
            if not codes_str:
                return []
            codes = [int(c) for c in codes_str.split("+")]
            return codes
    except (ValueError, AttributeError):
        pass
    
    return None


def is_error_response(response: str) -> bool:
    """Check if response indicates an error (format: g#@Ezzz)."""
    if not response:
        return False
    return "@E" in response


def parse_error_code(response: str) -> Optional[int]:
    """
    Parse error code from error response.
    
    Expected format: g#@Ezzz
    Returns: error code integer, or None if parse fails
    """
    if not is_error_response(response):
        return None
    
    try:
        match = re.search(r"@E(\d+)", response)
        if match:
            return int(match.group(1))
    except (ValueError, AttributeError):
        pass
    
    return None
