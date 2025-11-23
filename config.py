import json
import os
from logger_setup import log

CONFIG_FILE = 'settings.json'

CURRENT_APP_VERSION = "1.0.0"
VERSION_CHECK_URL = "https://gist.githubusercontent.com/YOUR_USERNAME/YOUR_GIST_ID/raw/version.json"

class ConfigManager:
    def __init__(self, file_path=CONFIG_FILE):
        self.file_path = file_path
        self.settings = self.load_settings()

    def load_settings(self):
        defaults = self._get_default_settings()
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r') as f:
                    settings = json.load(f)
                    self._merge_settings(defaults, settings)
                    return defaults
            except json.JSONDecodeError:
                log.error("Error reading settings.json, creating a new one.")
                return defaults
        else:
            return defaults

    def _merge_settings(self, defaults, loaded):
        for key, value in loaded.items():
            if isinstance(value, dict) and key in defaults and isinstance(defaults[key], dict):
                self._merge_settings(defaults[key], value)
            else:
                defaults[key] = value
    
    def _get_default_settings(self):
        return {
            "user": {
                "recipient_email": "",
                "encryption_password": "",
                "device_name": "My-Computer",
                "was_running": False,
                "local_save_enabled": False,
                "local_save_path": "",
                "prevent_sleep_while_running": True,
                "pin_login_enabled": False,
                "login_expiry_hours": 168,  # 7 days (168 hours) - user must login with email/password at least once every 7 days
                "refresh_token": None,
                "last_full_login_timestamp": 0,
                "pin_salt": None,
                "hashed_pin": None,
                "has_consented": False
            },
            "admin": {
                "admin_support_email": "frdsconnect7799@gmail.com",
                "log_send_interval_hours": 24
            },
            "emergency": {
                "hotkey": "<ctrl>+<alt>+e",
                "grace_period_sec": 5,
                "enabled": False,
                "data_sharing_consent": False,
                "user_phone": "",
                "emergency_contacts": []
            },
            "reporting": {
                "bundle_interval": 60,
                "bundle_time_of_day": "17:00",
                "bundle_schedule_mode": "interval"
            },

            # SMTP settings for sending emergency emails directly (fallback when no sender assignment exists)
            "smtp": {
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "smtp_email": "",
                "smtp_password": ""
            },
            
            # --- !! NEW: Stores the user's plan from Supabase !! ---
            "allowed_features": [], 
            
            # This stores the user's *choices*
            "user_preferences": {
                "screenshot_enabled": True,
                "screenshot_interval": 5,
                "screenshot_security": "high",
                "screenshot_destination": "bundle",
                "screenshot_start_time": "00:00", 
                "screenshot_end_time": "23:59",
                
                "telemetry_enabled": True,
                "telemetry_interval": 10,
                "telemetry_security": "high",
                "telemetry_destination": "bundle",
                "telemetry_start_time": "00:00", 
                "telemetry_end_time": "23:59",

                "activity_enabled": True,
                "activity_interval": 2,
                "activity_security": "high",
                "activity_destination": "instant",
                "activity_start_time": "00:00", 
                "activity_end_time": "23:59",

                "typed_activity_enabled": True,
                "typed_activity_interval": 5,
                "typed_activity_duration": 60,
                "typed_activity_security": "high",
                "typed_activity_destination": "bundle",
                "typed_activity_start_time": "00:00", 
                "typed_activity_end_time": "23:59",

                "camera_enabled": False,
                "camera_interval": 30,
                "camera_duration": 10,
                "camera_security": "zip",
                "camera_destination": "bundle",
                "camera_start_time": "00:00", 
                "camera_end_time": "23:59",

                "microphone_enabled": False,
                "microphone_interval": 30,
                "microphone_duration": 15,
                "microphone_security": "zip",
                "microphone_destination": "bundle",
                "microphone_start_time": "00:00", 
                "microphone_end_time": "23:59",

                "screen_record_enabled": False,
                "screen_record_interval": 60,
                "screen_record_duration": 5,
                "screen_record_security": "zip",
                "screen_record_destination": "bundle",
                "screen_record_start_time": "00:00", 
                "screen_record_end_time": "23:59"
            }
        }

    def save_settings(self):
        try:
            with open(self.file_path, 'w') as f:
                json.dump(self.settings, f, indent=4)
            log.info("Settings saved.")
        except Exception as e:
            log.error(f"Error saving settings: {e}")

    def get_settings(self):
        return self.settings

    def update_settings(self, new_settings_dict):
        self.settings = new_settings_dict
        self.save_settings()

config_manager = ConfigManager()