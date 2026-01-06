import cv2
import time
import os
from config import config_manager, DATA_DIR
from logger_setup import log

OUTPUT_DIR = os.path.join(DATA_DIR, "captures")

def get_device_name_and_time():
    try:
        device_name = config_manager.get_settings()["user"]["device_name"]
    except Exception:
        device_name = "My-Computer"
    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    return device_name, timestamp

def capture_camera_photo():
    """Captures a single photo from the default webcam."""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    device_name, timestamp = get_device_name_and_time()
    filename = os.path.join(OUTPUT_DIR, f"{device_name} - CameraPhoto - {timestamp}.jpg")
    
    cap = None
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            log.error("Cannot open default webcam for photo.")
            return None
        
        # Allow camera to adjust light (read a few frames)
        for _ in range(5):
            cap.read()
            
        ret, frame = cap.read()
        if ret:
            cv2.imwrite(filename, frame)
            log.info(f"Camera photo captured: {filename}")
            return filename
        else:
            log.error("Failed to capture frame for photo.")
            return None
    except Exception as e:
        log.error(f"Error capturing photo: {e}")
        return None
    finally:
        if cap:
            cap.release()
