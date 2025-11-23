import mss
import time
import os
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

def capture_screenshot():
    """ Captures a screenshot and saves it to a file """
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    try:
        with mss.mss() as sct:
            device_name, timestamp = get_device_name_and_time()
            filename = os.path.join(OUTPUT_DIR, f"{device_name} - Screenshot - {timestamp}.png")
            sct.shot(mon=1, output=filename)
            log.info(f"Screenshot captured: {filename}")
            return filename
    except Exception as e:
        log.error(f"Error capturing screenshot: {e}")
        return None