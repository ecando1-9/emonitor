import wmi
import hashlib
from logger_setup import log

# Cache the device hash to avoid regenerating it multiple times
_cached_device_hash = None

def get_device_hash():
    """
    Generates a unique, stable device hash using hardware identifiers.
    Cached after first generation to avoid repeated WMI calls.
    """
    global _cached_device_hash
    
    # Return cached hash if already generated
    if _cached_device_hash is not None:
        return _cached_device_hash
    
    log.info("Generating device fingerprint...")
    try:
        c = wmi.WMI()
        system_uuid = c.Win32_ComputerSystemProduct()[0].UUID
        board_serial = c.Win32_BaseBoard()[0].SerialNumber
        disk_serial = c.Win32_DiskDrive()[0].SerialNumber.strip()
        
        fingerprint_string = f"{system_uuid}-{board_serial}-{disk_serial}"
        hashed_fingerprint = hashlib.sha256(fingerprint_string.encode('utf-8')).hexdigest()
        
        log.info(f"Device hash generated: {hashed_fingerprint}")
        
        # Cache the hash
        _cached_device_hash = hashed_fingerprint
        return hashed_fingerprint
    except Exception as e:
        log.error(f"WMI failed, using fallback device hash: {e}")
        try:
            import socket
            hostname = socket.gethostname()
            fallback_hash = hashlib.sha256(hostname.encode('utf-8')).hexdigest()
            
            # Cache the fallback hash
            _cached_device_hash = fallback_hash
            return fallback_hash
        except Exception:
            # Cache the failure hash
            _cached_device_hash = "failed-to-generate-hash"
            return "failed-to-generate-hash"