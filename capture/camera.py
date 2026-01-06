import cv2
import time
import os
import threading
import subprocess
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

def capture_camera_video(duration_sec, record_audio=True):
    """Captures a video clip from the default webcam with audio for a specific duration.
    
    Args:
        duration_sec: Duration in seconds (max 30 for emergency mode)
        record_audio: If True, records audio with video using ffmpeg
    """
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    device_name, timestamp = get_device_name_and_time()
    
    # Limit duration to 30 seconds max for emergency mode
    if duration_sec > 30:
        duration_sec = 30
        log.warning(f"Duration limited to 30 seconds for emergency mode")
    
    # Try to use ffmpeg for video+audio recording (better quality)
    if record_audio:
        try:
            # Use ffmpeg to record video with audio - auto-detect devices
            filename = os.path.join(OUTPUT_DIR, f"{device_name} - Camera+Audio - {timestamp}.mp4")
            # Try multiple ffmpeg approaches for Windows
            # First try: Use default devices
            cmd1 = [
                'ffmpeg',
                '-f', 'gdigrab',
                '-framerate', '15',
                '-i', 'desktop',
                '-f', 'dshow',
                '-i', 'audio="default"',
                '-t', str(duration_sec),
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-c:a', 'aac',
                '-y',
                filename
            ]
            # Second try: DirectShow with video device
            cmd2 = [
                'ffmpeg',
                '-f', 'dshow',
                '-i', 'video="default":audio="default"',
                '-t', str(duration_sec),
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-c:a', 'aac',
                '-y',
                filename
            ]
            # Third try: Video only from camera index 0
            cmd3 = [
                'ffmpeg',
                '-f', 'dshow',
                '-video_device_number', '0',
                '-i', 'video="default"',
                '-f', 'dshow',
                '-i', 'audio="default"',
                '-t', str(duration_sec),
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-c:a', 'aac',
                '-y',
                filename
            ]
            
            for cmd, attempt_name in [(cmd2, "DirectShow default"), (cmd3, "DirectShow with device number"), (cmd1, "GDI grab")]:
                try:
                    log.info(f"Attempting {attempt_name} for camera+audio recording ({duration_sec} sec): {filename}")
                    result = subprocess.run(cmd, capture_output=True, timeout=duration_sec + 10)
                    if result.returncode == 0 and os.path.exists(filename) and os.path.getsize(filename) > 0:
                        log.info(f"Camera+audio recording finished: {filename}")
                        return filename
                    else:
                        error_msg = result.stderr.decode() if result.stderr else "Unknown error"
                        log.warning(f"{attempt_name} failed: {error_msg[:200]}")
                except subprocess.TimeoutExpired:
                    log.warning(f"{attempt_name} timed out")
                except Exception as e:
                    log.warning(f"{attempt_name} error: {e}")
            
            log.warning("All ffmpeg attempts failed, falling back to video-only recording.")
        except Exception as e:
            log.warning(f"ffmpeg not available or failed: {e}. Falling back to video-only recording.")
    
    # Fallback: Record video only with OpenCV
    filename = os.path.join(OUTPUT_DIR, f"{device_name} - Camera - {timestamp}.mp4")  # Changed to .mp4
    cap = None
    out = None
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            log.error("Cannot open default webcam.")
            return None
        frame_width = int(cap.get(3))
        frame_height = int(cap.get(4))
        fps = 10.0  # Reduced from 20 to 10 for smaller file size
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Changed from XVID to mp4v
        out = cv2.VideoWriter(filename, fourcc, fps, (frame_width, frame_height))
        start_time = time.time()
        log.info(f"Starting camera recording (video only) for {duration_sec} sec: {filename}")
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