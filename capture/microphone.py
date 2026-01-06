import sounddevice as sd
import wavio
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

def capture_microphone_audio(duration_sec):
    """Captures an audio clip from the default microphone for a specific duration.
    
    Args:
        duration_sec: Duration in seconds (max 30 for emergency mode)
    """
    # Limit duration to 30 seconds max for emergency mode
    if duration_sec > 30:
        duration_sec = 30
        log.warning(f"Microphone duration limited to 30 seconds for emergency mode")
    
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    device_name, timestamp = get_device_name_and_time()
    filename = os.path.join(OUTPUT_DIR, f"{device_name} - Microphone - {timestamp}.wav")
    try:
        fs = 44100
        log.info(f"Starting microphone recording for {duration_sec} sec: {filename}")
        recording = sd.rec(int(duration_sec * fs), samplerate=fs, channels=2, dtype='int16')
        sd.wait()
        wavio.write(filename, recording, fs, sampwidth=2)
        log.info(f"Microphone recording finished.")
        return filename
    except Exception as e:
        log.error(f"Error during microphone capture: {e}")
        return None