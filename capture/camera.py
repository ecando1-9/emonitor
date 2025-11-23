import cv2
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

def capture_camera_video(duration_sec):
    """Captures a video clip from the default webcam for a specific duration."""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    device_name, timestamp = get_device_name_and_time()
    filename = os.path.join(OUTPUT_DIR, f"{device_name} - Camera - {timestamp}.avi") 
    cap = None
    out = None
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            log.error("Cannot open default webcam.")
            return None
        frame_width = int(cap.get(3))
        frame_height = int(cap.get(4))
        fps = 20.0
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        out = cv2.VideoWriter(filename, fourcc, fps, (frame_width, frame_height))
        start_time = time.time()
        log.info(f"Starting camera recording for {duration_sec} sec: {filename}")
        while (time.time() - start_time) < duration_sec:
            ret, frame = cap.read()
            if ret:
                out.write(frame)
            else:
                break
        log.info(f"Camera recording finished.")
        return filename
    except Exception as e:
        log.error(f"Error during camera capture: {e}")
        return None
    finally:
        if cap:
            cap.release()
        if out:
            out.release()