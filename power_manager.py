import os
import platform
import sys
from logger_setup import log

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001

def prevent_sleep():
    """Tells Windows to prevent the system from going to sleep."""
    if platform.system() == "Windows":
        try:
            import ctypes
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
            log.info("System sleep has been PREVENTED.")
        except Exception as e:
            log.error(f"Failed to prevent system sleep: {e}")
    else:
        log.warning("Prevent sleep is only supported on Windows.")

def allow_sleep():
    """Tells Windows that the app is finished and the system can sleep normally."""
    if platform.system() == "Windows":
        try:
            import ctypes
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
            log.info("System sleep has been RE-ENABLED.")
        except Exception as e:
            log.error(f"Failed to allow system sleep: {e}")
    else:
        log.warning("Allow sleep is only supported on Windows.")