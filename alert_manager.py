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
    
    # Use the new emergency alert manager which handles everything:
    # 1. Database record creation
    # 2. Initial email notifications
    # 3. Continuous data capture protocol
    # 4. Periodic bundled updates
    try:
        from emergency_alert_manager import trigger_emergency_alert
        return trigger_emergency_alert("hotkey_or_button")
    except Exception as e:
        log.error(f"Failed to trigger emergency alert: {e}")
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
    
    # Check if emergency is actually active (more reliable than alert_in_progress flag)
    from emergency_alert_manager import is_emergency_active
    if is_emergency_active():
        log.warning("Emergency mode is already active. Ignoring new trigger.")
        from tkinter import messagebox
        messagebox.showinfo("Emergency Active", 
                           "Emergency mode is already running. Use the Dashboard to stop it first.")
        return
    
    # Clear any stale alert_in_progress flag
    if alert_in_progress.is_set():
        log.info("Clearing stale alert_in_progress flag")
        alert_in_progress.clear()
    
    # EMERGENCY MODE: Start immediately - skip or minimize grace period
    # Check grace period setting - if 0 or very short, skip window and activate immediately
    grace_period = emergency_settings.get("grace_period_sec", 5)
    if grace_period <= 1:
        # Grace period is 0-1 seconds - activate immediately
        log.info("Emergency Alert Triggered! Activating immediately (grace period <= 1 second)...")
        alert_in_progress.set()
        send_alert_to_supabase()
    else:
        # Show grace period window (but keep it short)
        log.info(f"Emergency Alert Triggered! Starting {grace_period} second grace period...")
        alert_in_progress.set()
        main_window_controller.after(0, open_grace_period_window, main_window_controller)

def open_grace_period_window(controller):
    global grace_period_window
    from ui.grace_period_ui import GracePeriodWindow
    
    # Close existing window if it exists
    if grace_period_window:
        try:
            grace_period_window.destroy()
        except Exception:
            pass
        grace_period_window = None
    
    # Create new grace period window
    grace_period_window = GracePeriodWindow(controller, on_cancel=cancel_alert, on_confirm=send_alert_to_supabase)
        
def cancel_alert():
    """Called by the UI to cancel the alert."""
    log.info("Alert CANCELLED by user.")
    global grace_period_window
    if grace_period_window:
        grace_period_window.destroy()
        grace_period_window = None
    alert_in_progress.clear()
    # User cancelled logic
    log.info("Cancellation processed. No emails will be sent.")

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