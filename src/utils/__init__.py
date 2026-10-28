"""Utility functions for common operations."""

import json
import hashlib
from typing import Any, Dict
from datetime import datetime

def generate_id(data: Any) -> str:
    """Generate a deterministic ID from data."""
    if isinstance(data, dict):
        data_str = json.dumps(data, sort_keys=True)
    else:
        data_str = str(data)
    
    return hashlib.md5(data_str.encode()).hexdigest()

def format_timestamp(timestamp: datetime = None) -> str:
    """Format timestamp for display."""
    if timestamp is None:
        timestamp = datetime.utcnow()
    return timestamp.isoformat() + 'Z'

def safe_get(dictionary: Dict, *keys: str, default: Any = None) -> Any:
    """Safely get nested dictionary values."""
    current = dictionary
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key, default)
        else:
            return default
    return current

__all__ = ['generate_id', 'format_timestamp', 'safe_get']