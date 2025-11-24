import threading
from pynput import keyboard
from logger_setup import log
from config import config_manager
from auth import auth_service
from device_fingerprint import get_device_hash
from capture.telemetry import get_location_info_data
from capture.activity import get_active_window_data
import os
import json
import scheduler 

hotkey_listener_thread = None
alert_in_progress = threading.Event()
grace_period_window = None

def get_data_for_alert():
    """Instantly gathers all data needed for an alert."""
    log.info("Gathering instant data for emergency alert...")
    location_data = {}
    try:
        location_data = get_location_info_data() 
    except Exception as e:
        log.error(f"Failed to get any location data: {e}")
        location_data = {"error": "Failed to get location."}
    activity_summary = "Could not get activity."
    try:
        activity_summary = get_active_window_data()
        log.info(f"Last known activity: {activity_summary}")
    except Exception as e:
        log.error(f"Failed to get activity data: {e}")
    return location_data, activity_summary

def send_alert_to_supabase():
    """Sends emergency alert via email and Supabase."""
    log.info("Grace period over. Sending emergency alert...")
    
    # Use the new emergency alert manager (sends email)
    try:
        from emergency_alert_manager import trigger_emergency_alert
        trigger_emergency_alert("hotkey_or_button")
        
        # Update dashboard button state immediately after emergency is triggered
        try:
            import sys
            main_window = sys.modules.get('ui.main_window')
            if main_window and hasattr(main_window, 'main_app'):
                from ui.dashboard_ui import DashboardFrame
                if DashboardFrame in main_window.main_app.frames:
                    dashboard_frame = main_window.main_app.frames[DashboardFrame]
                    if hasattr(dashboard_frame, 'update_emergency_button_state'):
                        # Update immediately and keep checking
                        dashboard_frame.after(100, dashboard_frame.update_emergency_button_state)
                        dashboard_frame.after(500, dashboard_frame.update_emergency_button_state)
                        dashboard_frame.after(1000, dashboard_frame.update_emergency_button_state)
                        log.info("Dashboard cancel button should now be visible")
        except Exception as update_error:
            log.debug(f"Could not update dashboard button state immediately: {update_error}")
    except Exception as e:
        log.error(f"Failed to send emergency alert via email: {e}")
    
    # Also try Supabase if available
    try:
        device_hash = get_device_hash()
        location, activity = get_data_for_alert()

        # --- !! THIS IS THE FIX for Bug 2 !! ---
        # We now send all data as a single JSON object
        alert_payload = {
            "device_hash": device_hash,
            "location": location,
            "activity": activity
        }
        
        res = auth_service.client.rpc("trigger_emergency_alert", {
            "alert_data": alert_payload
        }).execute()

        if res.data and res.data.get("success"):
            log.info(f"Successfully sent alert to Supabase. Alert ID: {res.data.get('alert_id')}")
            log.info("TRIGGERING EMERGENCY CAPTURE PROTOCOL!")
            # Import from emergency_alert_manager where the function is defined
            try:
                from emergency_alert_manager import run_emergency_capture_protocol
                threading.Thread(target=run_emergency_capture_protocol, daemon=True).start()
            except ImportError:
                log.warning("Could not import run_emergency_capture_protocol")
            return True
        else:
            log.error(f"Failed to send alert to Supabase: {res.data}")
            return False
            
    except Exception as e:
        log.error(f"Exception while sending alert to Supabase: {e}")
        return False

def trigger_alert_process(main_window_controller):
    """Starts the grace period and alert process."""
    # Check if emergency alert is enabled
    settings = config_manager.get_settings()
    emergency_settings = settings.get("emergency", {})
    
    if not emergency_settings.get("enabled", False):
        from tkinter import messagebox
        messagebox.showwarning("Emergency Alert Disabled", 
                              "Emergency Alert feature is disabled. Please enable it in Settings.")
        return
    
    if not emergency_settings.get("data_sharing_consent", False):
        from tkinter import messagebox
        messagebox.showwarning("Consent Required", 
                              "You must consent to data sharing in Emergency Alert settings before using this feature.")
        return
    
    if alert_in_progress.is_set():
        log.warning("Alert already in progress. Ignoring new trigger.")
        return
    log.info("Emergency Alert Triggered! Starting grace period...")
    alert_in_progress.set()
    main_window_controller.after(0, open_grace_period_window, main_window_controller)

def open_grace_period_window(controller):
    global grace_period_window
    from ui.grace_period_ui import GracePeriodWindow
    if grace_period_window:
        grace_period_window.lift()
    else:
        grace_period_window = GracePeriodWindow(controller, on_cancel=cancel_alert, on_confirm=send_alert_to_supabase)
        
def cancel_alert():
    """Called by the UI to cancel the alert."""
    log.info("Alert CANCELLED by user.")
    global grace_period_window
    if grace_period_window:
        grace_period_window.destroy()
        grace_period_window = None
    alert_in_progress.clear()

class HotkeyManager:
    def __init__(self, main_window_controller):
        self.main_window = main_window_controller
        self.hotkey_str = config_manager.get_settings()["emergency"]["hotkey"]
        self.listener = None
        
        # --- !! THIS IS THE FIX for Bug 1 !! ---
        # Changed 'self_hotkey_str' to 'self.hotkey_str'
        self.hotkey = keyboard.HotKey(
            keyboard.HotKey.parse(self.hotkey_str),
            self.on_hotkey_activate
        )
        self.listener = keyboard.GlobalHotKeys({
            self.hotkey_str: self.on_hotkey_activate
        })

    def on_hotkey_activate(self):
        log.warning(f"EMERGENCY HOTKEY ({self.hotkey_str}) PRESSED!")
        trigger_alert_process(self.main_window)
    def start(self):
        log.info(f"Starting global hotkey listener ({self.hotkey_str})...")
        self.listener.start()
    def stop(self):
        log.info("Stopping global hotkey listener...")
        if self.listener:
            self.listener.stop()
            self.listener = None

def start_hotkey_listener(main_window_controller):
    global hotkey_listener_thread
    if hotkey_listener_thread is None:
        try:
            manager = HotkeyManager(main_window_controller)
            hotkey_listener_thread = manager
            manager.start()
        except Exception as e:
            log.error(f"Failed to start hotkey listener: {e}")

def stop_hotkey_listener():
    global hotkey_listener_thread
    if hotkey_listener_thread:
        hotkey_listener_thread.stop()
        hotkey_listener_thread = None