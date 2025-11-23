import pygetwindow as gw
import time
import os
import json
from config import config_manager
from logger_setup import log

OUTPUT_DIR = "captures"

def get_device_name_and_time():
    try:
        device_name = config_manager.get_settings()["user"]["device_name"]
    except Exception:
        device_name = "My-Computer"
    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    return device_name, timestamp

def get_active_window_data():
    """Instantly gets the active window title as a string."""
    try:
        active_window = gw.getActiveWindow()
        title = active_window.title if active_window else "No active window"
        return title
    except Exception as e:
        log.error(f"Error getting active window data: {e}")
        return "Error: Could not get window title"

def capture_active_window():
    """ Captures the title of the currently active window to a file"""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    try:
        device_name, timestamp = get_device_name_and_time()
        filename = os.path.join(OUTPUT_DIR, f"{device_name} - Activity - {timestamp}.json")
        title = get_active_window_data()
        data = {
            "timestamp": time.time(),
            "active_window_title": title
        }
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
        log.info(f"Activity captured: {title}")
        return filename
    except Exception as e:
        log.error(f"Error capturing active window: {e}")
        return None