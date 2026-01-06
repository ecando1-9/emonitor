"""
Timezone utility for consistent timestamp handling
Ensures all timestamps are in local timezone with proper formatting
"""

from datetime import datetime, timezone
import time

def get_local_timestamp_iso():
    """
    Get current local timestamp in ISO format with timezone.
    
    Returns:
        str: ISO 8601 formatted timestamp with timezone offset
        Example: "2026-01-04T18:21:24+05:30"
    """
    # Get current time with timezone awareness
    now = datetime.now().astimezone()
    return now.isoformat()

def get_local_timestamp_readable():
    """
    Get current local timestamp in human-readable format.
    
    Returns:
        str: Readable timestamp
        Example: "2026-01-04 18:21:24 IST"
    """
    now = datetime.now().astimezone()
    # Get timezone name
    tz_name = time.tzname[time.daylight]
    return f"{now.strftime('%Y-%m-%d %H:%M:%S')} {tz_name}"

def get_utc_timestamp_iso():
    """
    Get current UTC timestamp in ISO format.
    
    Returns:
        str: ISO 8601 formatted UTC timestamp
        Example: "2026-01-04T12:51:24+00:00"
    """
    now = datetime.now(timezone.utc)
    return now.isoformat()

def format_timestamp_local(iso_timestamp):
    """
    Convert ISO timestamp to local timezone.
    
    Args:
        iso_timestamp: ISO formatted timestamp string
        
    Returns:
        str: Timestamp converted to local timezone
    """
    try:
        dt = datetime.fromisoformat(iso_timestamp)
        local_dt = dt.astimezone()
        return local_dt.isoformat()
    except Exception:
        return iso_timestamp

# For backward compatibility
def now_iso():
    """Alias for get_local_timestamp_iso()"""
    return get_local_timestamp_iso()

if __name__ == "__main__":
    print("Testing timezone utilities:")
    print(f"Local ISO: {get_local_timestamp_iso()}")
    print(f"Local Readable: {get_local_timestamp_readable()}")
    print(f"UTC ISO: {get_utc_timestamp_iso()}")
