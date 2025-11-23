import cv2
import numpy as np
import mss
import time
import os
from config import config_manager
from logger_setup import log

OUTPUT_DIR = "captures"
MAX_FILE_SIZE_MB = 20
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

def get_device_name_and_time():
    try:
        device_name = config_manager.get_settings()["user"]["device_name"]
    except Exception:
        device_name = "My-Computer"
    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    return device_name, timestamp

def create_video_writer(filename, width, height):
    """Creates a new OpenCV VideoWriter object"""
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    return cv2.VideoWriter(filename, fourcc, 15.0, (width, height))

def capture_screen_record(duration_sec, process_callback):
    """
    Captures the screen for a set duration, splitting into chunks
    based on file size.
    """
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    log.info(f"Starting screen recording session for {duration_sec} seconds...")
    start_time = time.time()
    chunk_index = 1
    try:
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            width, height = monitor["width"], monitor["height"]
            
            device_name, timestamp = get_device_name_and_time()
            current_chunk_filename = os.path.join(
                OUTPUT_DIR, 
                f"{device_name} - Screen-Record - {timestamp} (Chunk {chunk_index}).avi"
            )
            video_writer = create_video_writer(current_chunk_filename, width, height)
            
            while (time.time() - start_time) < duration_sec:
                img = sct.grab(monitor)
                frame = np.array(img)
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                video_writer.write(frame)
                
                if os.path.getsize(current_chunk_filename) > MAX_FILE_SIZE_BYTES:
                    log.info(f"Chunk {chunk_index} full ({MAX_FILE_SIZE_MB}MB). Finalizing.")
                    video_writer.release()
                    process_callback(current_chunk_filename, "screen_record")
                    
                    chunk_index += 1
                    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
                    current_chunk_filename = os.path.join(
                        OUTPUT_DIR, 
                        f"{device_name} - Screen-Record - {timestamp} (Chunk {chunk_index}).avi"
                    )
                    video_writer = create_video_writer(current_chunk_filename, width, height)
                    log.info(f"Starting new chunk: {current_chunk_filename}")
            
            log.info("Screen recording session finished. Finalizing last chunk.")
            video_writer.release()
            process_callback(current_chunk_filename, "screen_record")
    except Exception as e:
        log.error(f"Error during screen recording: {e}")
    finally:
        if 'video_writer' in locals() and video_writer.isOpened():
            video_writer.release()