import wmi
import hashlib
from logger_setup import log

def get_device_hash():
    """
    Generates a unique, stable device hash using hardware identifiers.
    """
    log.info("Generating device fingerprint...")
    try:
        c = wmi.WMI()
        system_uuid = c.Win32_ComputerSystemProduct()[0].UUID
        board_serial = c.Win32_BaseBoard()[0].SerialNumber
        disk_serial = c.Win32_DiskDrive()[0].SerialNumber.strip()
        
        fingerprint_string = f"{system_uuid}-{board_serial}-{disk_serial}"
        hashed_fingerprint = hashlib.sha256(fingerprint_string.encode('utf-8')).hexdigest()
        
        log.info(f"Device hash generated: {hashed_fingerprint}")
        return hashed_fingerprint
    except Exception as e:
        log.error(f"WMI failed, using fallback device hash: {e}")
        try:
            import socket
            hostname = socket.gethostname()
            return hashlib.sha256(hostname.encode('utf-8')).hexdigest()
        except Exception:
            return "failed-to-generate-hash"