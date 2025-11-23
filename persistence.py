import sys
import os
import winreg
import hashlib
import binascii
from logger_setup import log
try:
    import pythoncom
    from win32com.client import Dispatch
except ImportError:
    log.error("pywin32 library not found. Run 'pip install pywin32' to enable shortcut creation.")
    pythoncom = None # type: ignore
    Dispatch = None # type: ignore

APP_NAME = "eMonitor"
REG_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
EMERGENCY_SHORTCUT_NAME = "eMonitor EMERGENCY ALERT.lnk"

# Power Management
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001

def prevent_sleep():
    if "win" in sys.platform:
        try:
            import ctypes
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
            log.info("System sleep has been PREVENTED.")
        except Exception as e:
            log.error(f"Failed to prevent system sleep: {e}")
    else:
        log.warning("Prevent sleep is only supported on Windows.")

def allow_sleep():
    if "win" in sys.platform:
        try:
            import ctypes
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
            log.info("System sleep has been RE-ENABLED.")
        except Exception as e:
            log.error(f"Failed to allow system sleep: {e}")
    else:
        log.warning("Allow sleep is only supported on Windows.")

# Shortcut Functions
def get_desktop_path():
    """Finds the user's Desktop folder."""
    return os.path.join(os.path.expanduser("~"), "Desktop")

def get_bat_path(bat_name="start_emergency_alert.bat"):
    """Gets the full path to one of our .bat files."""
    return os.path.abspath(bat_name)
    
def create_desktop_shortcut(on=True):
    """Creates or deletes the .lnk shortcut on the user's desktop."""
    if "win" not in sys.platform or pythoncom is None:
        log.warning("Shortcut creation is only supported on Windows with pywin32.")
        raise NotImplementedError("Shortcut creation only supported on Windows with pywin32")
    try:
        pythoncom.CoInitialize() # Initialize COM library
        desktop = get_desktop_path()
        shortcut_path = os.path.join(desktop, EMERGENCY_SHORTCUT_NAME)

        if on:
            bat_path = get_bat_path("start_emergency_alert.bat")
            if not os.path.exists(bat_path):
                log.error(f"Cannot create shortcut. Missing file: {bat_path}")
                raise FileNotFoundError(f"Missing {bat_path}")
            log.info(f"Creating emergency shortcut at: {shortcut_path}")
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.Targetpath = bat_path
            shortcut.WorkingDirectory = os.path.dirname(bat_path)
            shortcut.IconLocation = sys.executable
            shortcut.Description = "Trigger eMonitor Emergency Alert"
            shortcut.save()
            log.info("Shortcut created.")
        else:
            if os.path.exists(shortcut_path):
                log.info(f"Removing emergency shortcut from: {shortcut_path}")
                os.remove(shortcut_path)
                log.info("Shortcut removed.")
            else:
                log.info("Shortcut already removed.")
    except Exception as e:
        log.error(f"Failed to create/remove shortcut: {e}")
        raise
    finally:
        pythoncom.CoUninitialize()

# Startup Management
def get_run_command():
    python_exe_path = sys.executable
    script_path = os.path.abspath("main.py")
    # Add --minimized flag so app starts hidden to tray on boot
    return f'"{python_exe_path}" "{script_path}" --minimized'

def set_startup(on=True):
    if "win" not in sys.platform:
        log.warning("Startup persistence is only supported on Windows.")
        return
    log.info(f"Setting startup persistence to: {on}")
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, 
            REG_KEY_PATH, 
            0, 
            winreg.KEY_ALL_ACCESS
        ) as key:
            if on:
                command = get_run_command()
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, command)
                log.info(f"Successfully added to startup: {command}")
            else:
                winreg.DeleteValue(key, APP_NAME)
                log.info(f"Successfully removed from startup.")
    except FileNotFoundError:
        if on:
            log.error("Registry key not found. Failed to set startup.")
            raise
    except Exception as e:
        log.error(f"Failed to access registry: {e}")
        raise

def check_startup():
    if "win" not in sys.platform:
        return False
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, 
            REG_KEY_PATH, 
            0, 
            winreg.KEY_READ
        ) as key:
            winreg.QueryValueEx(key, APP_NAME)
            return True
    except FileNotFoundError:
        return False
    except Exception as e:
        log.error(f"Error checking startup: {e}")
        return False

# PIN Hashing
def hash_pin(pin: str):
    salt = os.urandom(16)
    salt_hex = salt.hex()
    hashed = hashlib.pbkdf2_hmac('sha256', pin.encode('utf-8'), salt, 100000)
    hashed_hex = hashed.hex()
    return salt_hex, hashed_hex

def verify_pin(pin: str, salt_hex: str, hashed_hex: str):
    try:
        salt = binascii.unhexlify(salt_hex)
        stored_hash = binascii.unhexlify(hashed_hex)
        new_hash = hashlib.pbkdf2_hmac('sha256', pin.encode('utf-8'), salt, 100000)
        return new_hash == stored_hash
    except Exception as e:
        log.error(f"Error verifying PIN: {e}")
        return False