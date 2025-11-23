import time
import os
import json
from pynput import keyboard
import threading
from config import config_manager
from logger_setup import log

OUTPUT_DIR = "captures"

data_lock = threading.Lock()
key_counts = {
    "total_presses": 0
}

listener_thread = None
listener_running = False

def on_press(key):
    """Callback for when a key is pressed. Just increments a counter."""
    global key_counts
    with data_lock:
        key_counts["total_presses"] += 1
    if not listener_running:
        return False # Stop the listener

def start_key_listener():
    """Starts the key listener thread."""
    global listener_thread, listener_running
    if listener_thread is None or not listener_thread.is_alive():
        log.info("Starting typed-activity listener thread...")
        listener_running = True
        try:
            listener_thread = keyboard.Listener(on_press=on_press)
            listener_thread.start()
            log.info("Typed-activity listener started.")
        except Exception as e:
            log.error(f"Failed to start typed-activity listener: {e}")

def stop_key_listener():
    """Stops the key listener thread."""
    global listener_thread, listener_running
    log.info("Stopping typed-activity listener...")
    listener_running = False
    if listener_thread:
        try:
            listener_thread.stop()
        except Exception as e:
            log.error(f"Error stopping key listener: {e}")
        listener_thread = None

def get_device_name_and_time():
    try:
        device_name = config_manager.get_settings()["user"]["device_name"]
    except Exception:
        device_name = "My-Computer"
    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    return device_name, timestamp

def capture_typed_activity(duration_sec):
    """
    Captures the *count* of key presses over a duration.
    This is NOT a keylogger.
    """
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    global key_counts
    with data_lock:
        key_counts = {"total_presses": 0}
    
    log.info(f"Starting typed-activity capture for {duration_sec} seconds...")
    time.sleep(duration_sec)
    log.info("Finished typed-activity capture.")
    
    try:
        device_name, timestamp = get_device_name_and_time()
        filename = os.path.join(OUTPUT_DIR, f"{device_name} - Typed-Activity - {timestamp}.json")
        
        with data_lock:
            final_data = {
                "timestamp": time.time(),
                "duration_seconds": duration_sec,
                "total_key_presses": key_counts["total_presses"]
            }
            key_counts = {"total_presses": 0}

        if final_data["total_key_presses"] == 0:
            log.info("No typing activity detected. Skipping file creation.")
            return None
            
        with open(filename, 'w') as f:
            json.dump(final_data, f, indent=4)
            
        log.info(f"Typed-Activity captured: {filename}")
        return filename
    except Exception as e:
        log.error(f"Error capturing typed-activity: {e}")
        return None