def hex_formatter(data: bytes) -> str:
    """Convert bytes data to a formatted hex string."""
    return " ".join(f"{byte:02X}" for byte in data)
