import json
import os
from logger_setup import log

# --- Centralized Data Directory ---
# --- Centralized Data Directory ---
# Professional Data Storage: Use %APPDATA% (Hidden & Persistent)
import sys
if sys.platform == "win32":
    app_data_roaming = os.getenv('APPDATA')
    if app_data_roaming:
        BASE_DIR = os.path.join(app_data_roaming, "eMonitor")
    else:
        # Fallback if APPDATA env var is missing
        BASE_DIR = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "eMonitor")
else:
    # Linux/Mac fallback (for dev)
    BASE_DIR = os.path.join(os.path.expanduser("~"), ".eMonitor")

if not os.path.exists(BASE_DIR):
    try:
        os.makedirs(BASE_DIR)
    except Exception as e:
        # Emergency fallback to temp if permissions fail
        import tempfile
        BASE_DIR = os.path.join(tempfile.gettempdir(), "eMonitor")
        if not os.path.exists(BASE_DIR): os.makedirs(BASE_DIR)

DATA_DIR = os.path.join(BASE_DIR, "app_data")

# Create data directory if it doesn't exist
if not os.path.exists(DATA_DIR):
    try:
        os.makedirs(DATA_DIR)
        # Verify it was created
        if not os.path.exists(DATA_DIR):
            raise OSError("Directory not created")
            
        # Hide the folder on Windows (Security requirement)
        if os.name == 'nt':
            import ctypes
            ctypes.windll.kernel32.SetFileAttributesW(DATA_DIR, 2) # 2 = Hidden
    except Exception as e:
        print(f"CRITICAL: Failed to create data directory {DATA_DIR}: {e}")
        # Fallback to current directory
        DATA_DIR = BASE_DIR

CONFIG_FILE = os.path.join(DATA_DIR, 'settings.json')

# Migration: Move old settings.json if it exists
try:
    OLD_CONFIG_FILE = os.path.join(BASE_DIR, 'settings.json')
    if os.path.exists(OLD_CONFIG_FILE) and not os.path.exists(CONFIG_FILE):
        import shutil
        shutil.move(OLD_CONFIG_FILE, CONFIG_FILE)
        from logger_setup import log
        log.info(f"Migrated settings.json to {DATA_DIR}")
except Exception as e:
    print(f"Migration Warning: {e}")

CURRENT_APP_VERSION = "1.0.0"
VERSION_CHECK_URL = "https://gist.githubusercontent.com/YOUR_USERNAME/YOUR_GIST_ID/raw/version.json"

class ConfigManager:
    def __init__(self, file_path=CONFIG_FILE):
        self.file_path = file_path
        self.current_user_id = None  # Track which user's settings are loaded
        self.settings = self.load_settings()

    def load_settings(self):
        """Load settings from local file (used as cache/offline mode)"""
        defaults = self._get_default_settings()
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r') as f:
                    settings = json.load(f)
                    self._merge_settings(defaults, settings)
                    # Track which user these settings belong to
                    self.current_user_id = settings.get("_user_id", None)
                    return defaults
            except json.JSONDecodeError:
                log.error("Error reading settings.json, creating a new one.")
                return defaults
        else:
            return defaults
    
    def load_user_settings_from_db(self, user_id, supabase_client):
        """Load user-specific settings from database"""
        try:
            result = supabase_client.table("user_settings").select("settings").eq("user_id", user_id).execute()
            
            if result.data and len(result.data) > 0:
                # User has settings in database - load them
                user_settings = result.data[0]["settings"]
                log.info(f"Loaded settings from database for user {user_id}")
                
                # Merge with defaults to ensure all keys exist
                defaults = self._get_default_settings()
                self._merge_settings(defaults, user_settings)
                defaults["_user_id"] = user_id  # Track user
                
                self.settings = defaults
                self.current_user_id = user_id
                self.save_settings()  # Cache locally
                return True
            else:
                # First time - save CURRENT settings to database (not defaults)
                log.info(f"First login - saving current settings to database for user {user_id}")
                
                # Use current settings (preserves any settings user already configured)
                current_settings = self.settings.copy()
                current_settings["_user_id"] = user_id
                
                # Remove _user_id before saving to database
                settings_to_save = {k: v for k, v in current_settings.items() if k != "_user_id"}
                
                supabase_client.table("user_settings").insert({
                    "user_id": user_id,
                    "settings": settings_to_save
                }).execute()
                
                self.settings = current_settings
                self.current_user_id = user_id
                self.save_settings()  # Cache locally
                log.info("Current settings saved to database successfully")
                return True
                
        except Exception as e:
            log.error(f"Error loading user settings from database: {e}")
            log.warning("Using local settings as fallback")
            return False

    def _merge_settings(self, defaults, loaded):
        for key, value in loaded.items():
            if isinstance(value, dict) and key in defaults and isinstance(defaults[key], dict):
                self._merge_settings(defaults[key], value)
            else:
                defaults[key] = value
    
    def _get_default_settings(self):
        return {
            "_user_id": None,  # Track which user these settings belong to
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
                "admin_support_email": "ecando976@gmail.com",
                "log_send_interval_hours": 24
            },
            "emergency": {
                "hotkey": "<ctrl>+<alt>+e",
                "grace_period_sec": 5,
                "enabled": False,
                "data_sharing_consent": False,
                "user_phone": "",
                "user_name": "",
                "emergency_email": "",
                "emergency_contacts": [],
                "data_sharing_preferences": {
                    "screenshot": False,
                    "device_info": False,
                    "last_location": False,
                    "activity_summary": False,
                    "logs": False,
                    "camera": False,
                    "microphone": False,
                    "screen_record": False
                },
                "max_duration_minutes": 59,
                "duration_unit": "minutes",
                "email_interval_seconds": 30
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
        """Save settings locally (cache) and to database if user is logged in"""
        # Save locally
        try:
            with open(self.file_path, 'w') as f:
                json.dump(self.settings, f, indent=4)
            log.info("Settings saved locally.")
        except Exception as e:
            log.error(f"Error saving settings locally: {e}")
        
        # Save to database if user is logged in
        if self.current_user_id:
            try:
                from auth import auth_service
                if auth_service and auth_service.client:
                    # Remove _user_id before saving to database
                    settings_to_save = {k: v for k, v in self.settings.items() if k != "_user_id"}
                    
                    auth_service.client.table("user_settings").update({
                        "settings": settings_to_save,
                        "updated_at": "now()"
                    }).eq("user_id", self.current_user_id).execute()
                    log.info("Settings synced to database.")
            except Exception as e:
                log.warning(f"Could not sync settings to database: {e}")

    def get_settings(self):
        return self.settings

    def update_settings(self, new_settings_dict):
        # Preserve user_id
        if "_user_id" in self.settings:
            new_settings_dict["_user_id"] = self.settings["_user_id"]
        self.settings = new_settings_dict
        self.save_settings()

config_manager = ConfigManager()