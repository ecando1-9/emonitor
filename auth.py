import os
import time
from supabase import create_client, Client
from dotenv import load_dotenv
from logger_setup import log
from device_fingerprint import get_device_hash
from config import config_manager
from persistence import hash_pin, verify_pin

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_ANON_KEY")
if not url or not key:
    log.critical("SUPABASE_URL and SUPABASE_ANON_KEY must be set in .env file")
    raise EnvironmentError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in .env file")
supabase: Client = create_client(url, key)

class AuthService:
    def __init__(self):
        self.client = supabase
        self.current_user = None
        self.session = None
        self.subscription_data = None # This will hold the user's plan info
        self._sender_cache = None  # Cache for sender credentials
        self._sender_cache_time = 0  # Timestamp of cache
        self._sender_cache_ttl = 300  # Cache TTL in seconds (5 minutes)
        self._last_warning_time = 0  # Throttle warning messages
        self._warning_throttle = 300  # Only warn once per 5 minutes

    def sign_up(self, email, password):
        """
        Signs up a new user.
        The database trigger 'handle_new_user_setup' will do all the heavy lifting.
        """
        try:
            device_hash = get_device_hash()
            if "failed" in device_hash:
                return {"success": False, "error": "Could not get device ID."}
            
            log.info("Device hash generated. Attempting to create user...")
            
            # We just sign up the user and pass the device_hash in the metadata
            # The trigger (handle_new_user_setup) will see this and run.
            res = self.client.auth.sign_up({
                "email": email,
                "password": password,
                "options": { 
                    "data": { 
                        "device_hash": device_hash 
                    }
                }
            })
            
            if res.user:
                log.info(f"Sign up successful for {email}. Trigger will handle setup.")
                # We must wait a moment for the trigger to run *before* we sign in
                time.sleep(1.5) # Wait 1.5 seconds for the database trigger
                return self.sign_in(email, password) 
            if res.api_error:
                log.error(f"Sign up failed: {res.api_error.message}")
                return {"success": False, "error": res.api_error.message}
                
        except Exception as e:
            log.error(f"Sign up exception: {e}")
            if "Trial limit reached" in str(e):
                return {"success": False, "error": "Trial limit reached for this device (maximum 5 trials). Contact support."}
            if "CRITICAL" in str(e):
                return {"success": False, "error": "No available sender emails in the pool. Please contact support."}
            return {"success": False, "error": "An unknown error occurred during signup."}

    def sign_in(self, email, password):
        """Signs in and fetches the user's subscription status."""
        try:
            res = self.client.auth.sign_in_with_password({"email": email, "password": password})
            if res.user:
                self.current_user = res.user
                self.session = res.session
                log.info(f"Sign in successful for {res.user.email}")
                
                self.save_full_login_session(res.session.refresh_token)
                
                # --- !! NEW: FETCH SUBSCRIPTION !! ---
                sub_data = self.get_subscription_status()
                # This check fixes the 'NoneType' crash
                if sub_data is None:
                    return {"success": False, "error": "Failed to fetch subscription. User record may be incomplete."}
                
                return {"success": True, "user": res.user, "subscription": sub_data}
                
            if res.api_error:
                log.error(f"Sign in failed: {res.api_error.message}")
                return {"success": False, "error": res.api_error.message}
        except Exception as e:
            log.error(f"Sign in exception: {e}")
            return {"success": False, "error": str(e)}

    def check_password(self, password_to_check):
        if not self.current_user:
            log.error("Password check failed: No user is logged in.")
            return False
        current_email = self.current_user.email
        try:
            res = self.client.auth.sign_in_with_password({
                "email": current_email, 
                "password": password_to_check
            })
            if res.user:
                log.info("Password verification successful.")
                return True
            else:
                log.warning("Password verification failed (incorrect password).")
                return False
        except Exception as e:
            log.error(f"Password verification exception: {e}")
            return False

    def check_login_state(self):
        """Decides if we show PIN or full Login."""
        settings = config_manager.get_settings()["user"]
        
        if not settings.get("pin_login_enabled") or not settings.get("refresh_token") or not settings.get("hashed_pin"):
            return 'show_login_normal'
        
        last_login_time = settings.get("last_full_login_timestamp", 0)
        expiry_hours = settings.get("login_expiry_hours", 168)  # Default to 7 days
        expiry_seconds = expiry_hours * 3600
        time_elapsed = time.time() - last_login_time
        
        if time_elapsed > expiry_seconds:
            days = expiry_hours / 24
            log.info(f"PIN has expired ({days} days / {expiry_hours} hours). Forcing full email/password login.")
            self.full_logout()
            return 'show_login_expired'
        
        return 'show_pin'

    def login_with_token_and_pin(self, pin):
        """Attempts to log in with token AND verify PIN."""
        token = config_manager.get_settings()["user"].get("refresh_token")
        if not token:
            log.error("Token login failed: No token found.")
            return False, "No login session saved. Please log in with Email/Password.", None
            
        if not self.check_pin(pin):
            log.warning("Incorrect PIN entered.")
            return False, "Incorrect PIN.", None
            
        try:
            log.info("PIN correct. Attempting to log in with refresh token...")
            res = self.client.auth.set_session(token)
            
            if res.user:
                self.current_user = res.user
                self.session = res.session
                self.save_refresh_token_only(res.session.refresh_token)
                log.info("Refresh token login successful.")
                
                sub_data = self.get_subscription_status()
                # This check fixes the 'NoneType' crash
                if sub_data is None:
                    return {"success": False, "error": "Failed to fetch subscription. User record may be incomplete."}
                return True, "Login successful.", sub_data
            else:
                log.warning("Refresh token was invalid or expired.")
                self.full_logout()
                return False, "Your session expired. Please log in with your full password.", None
        except Exception as e:
            log.error(f"Token login failed: {e}")
            self.full_logout()
            return False, "Your session expired. Please log in with your full password.", None

    def save_full_login_session(self, token):
        """Saves token AND updates 20-hour timestamp."""
        settings = config_manager.get_settings()
        settings["user"]["refresh_token"] = token
        settings["user"]["last_full_login_timestamp"] = time.time()
        config_manager.update_settings(settings)
        log.info("Saved refresh token and 20-hour login timestamp.")
        
    def save_refresh_token_only(self, token):
        """Just saves the token, does not update the timestamp."""
        settings = config_manager.get_settings()
        settings["user"]["refresh_token"] = token
        config_manager.update_settings(settings)
        log.info("Refreshed session token.")
        
    def full_logout(self):
        """Clears all saved login data (token, pin, timestamp)"""
        log.info("Clearing all saved session data.")
        settings = config_manager.get_settings()
        settings["user"]["refresh_token"] = None
        settings["user"]["pin_login_enabled"] = False
        settings["user"]["pin_salt"] = None
        settings["user"]["hashed_pin"] = None
        settings["user"]["last_full_login_timestamp"] = 0
        settings["allowed_features"] = [] # Clear allowed features
        config_manager.update_settings(settings)
        self.subscription_data = None
        # Clear sender cache on logout
        self._sender_cache = None
        self._sender_cache_time = 0

    def set_new_pin(self, pin):
        """Hashes and saves a new PIN."""
        salt_hex, hashed_hex = hash_pin(pin)
        settings = config_manager.get_settings()
        settings["user"]["pin_salt"] = salt_hex
        settings["user"]["hashed_pin"] = hashed_hex
        settings["user"]["pin_login_enabled"] = True
        config_manager.update_settings(settings)
        log.info("New PIN has been set and PIN login enabled.")

    def check_pin(self, pin):
        """Checks an entered PIN against the saved hash."""
        settings = config_manager.get_settings()
        salt_hex = settings["user"]["pin_salt"]
        hashed_hex = settings["user"]["hashed_pin"]
        if not salt_hex or not hashed_hex:
            log.error("PIN check failed: No PIN is set.")
            return False
        return verify_pin(pin, salt_hex, hashed_hex)

    def send_password_reset_email(self, email):
        try:
            self.client.auth.reset_password_for_email(email)
            log.info(f"Password reset email sent to {email}")
            return {"success": True}
        except Exception as e:
            log.error(f"Password reset exception: {e}")
            return {"success": False, "error": str(e)}

    def get_sender_assignment(self, use_cache=True):
        """Fetch SMTP sender credentials for the current user from sender_pool database table.

        Queries the sender_pool table to get an active sender with the lowest assigned_count.
        This keeps all sensitive credentials only in the database, not hard-coded in the app.
        
        Falls back to config SMTP settings if sender_pool is empty or has no active senders.
        
        Uses caching to avoid repeated database queries and log spam.
        """
        if not self.current_user:
            return {"success": False, "error": "User not logged in"}

        # Check cache first (if enabled and not expired)
        current_time = time.time()
        if use_cache and self._sender_cache and (current_time - self._sender_cache_time) < self._sender_cache_ttl:
            return self._sender_cache

        # Throttle warning messages (only log once per 5 minutes)
        should_log_warning = (current_time - self._last_warning_time) >= self._warning_throttle

        try:
            # Query sender_pool table from database - get active senders ordered by assigned_count
            log.debug("Querying sender_pool table from database...")
            
            # First, try to get all senders to debug
            all_senders_res = (
                self.client
                .from_("sender_pool")
                .select("id, smtp_email, smtp_server, smtp_port, smtp_password, is_active, assigned_count, max_users")
                .execute()
            )
            
            if all_senders_res.data:
                log.debug(f"Found {len(all_senders_res.data)} total senders in pool")
                for s in all_senders_res.data:
                    log.debug(f"  - {s.get('smtp_email')}: is_active={s.get('is_active')} (type: {type(s.get('is_active'))})")
            
            # Query for active senders - handle both boolean true and string "true"/"Active"
            res = (
                self.client
                .from_("sender_pool")
                .select("id, smtp_email, smtp_server, smtp_port, smtp_password, is_active, assigned_count, max_users")
                .eq("is_active", True)
                .order("assigned_count", desc=False)
                .limit(1)
                .execute()
            )

            # Check if we got any data from the database
            if res.data and len(res.data) > 0:
                row = res.data[0]
                sender_id = row.get("id")
                
                if should_log_warning:
                    log.info(f"Found active sender in sender_pool: {row.get('smtp_email')} (ID: {sender_id})")
                
                # Check if sender has reached max_users limit
                max_users = row.get("max_users", 100)
                assigned_count = row.get("assigned_count", 0)
                
                if max_users is not None and assigned_count is not None and assigned_count >= max_users:
                    if should_log_warning:
                        log.warning(f"Sender {row.get('smtp_email')} has reached max_users limit ({assigned_count}/{max_users}). Trying next sender...")
                    # Try to find another sender
                    res2 = (
                        self.client
                        .from_("sender_pool")
                        .select("id, smtp_email, smtp_server, smtp_port, smtp_password, is_active, assigned_count, max_users")
                        .eq("is_active", True)
                        .neq("id", sender_id)
                        .order("assigned_count", desc=False)
                        .limit(1)
                        .execute()
                    )
                    
                    if res2.data and len(res2.data) > 0:
                        row = res2.data[0]
                        sender_id = row.get("id")
                        if should_log_warning:
                            log.info(f"Using alternative sender: {row.get('smtp_email')} (ID: {sender_id})")
                    else:
                        if should_log_warning:
                            log.warning("No alternative active sender found. Falling back to config SMTP.")
                        row = None
                
                if row:
                    # Increment assigned_count in database (optional - can be done asynchronously)
                    try:
                        if sender_id:
                            new_count = (row.get("assigned_count", 0) or 0) + 1
                            self.client.from_("sender_pool").update({
                                "assigned_count": new_count
                            }).eq("id", sender_id).execute()
                            log.debug(f"Updated assigned_count for sender {sender_id} to {new_count}")
                    except Exception as update_error:
                        if should_log_warning:
                            log.warning(f"Failed to update assigned_count: {update_error}")
                    
                    # Cache and return sender credentials from database
                    result = {
                        "success": True,
                        "data": {
                            "smtp_server": row["smtp_server"],
                            "smtp_port": int(row["smtp_port"]) if row.get("smtp_port") else 587,
                            "smtp_email": row["smtp_email"],
                            "smtp_password": row["smtp_password"],
                        },
                    }
                    self._sender_cache = result
                    self._sender_cache_time = current_time
                    return result
            
            # No active sender found in database - try querying without is_active filter to see what we have
            if should_log_warning:
                log.warning("No active sender found in sender_pool database table. Checking config fallback...")
                # Debug: Check if there are any senders at all
                debug_res = (
                    self.client
                    .from_("sender_pool")
                    .select("id, smtp_email, is_active")
                    .limit(5)
                    .execute()
                )
                if debug_res.data:
                    log.warning(f"Found {len(debug_res.data)} sender(s) in pool, but none are active:")
                    for s in debug_res.data:
                        log.warning(f"  - {s.get('smtp_email')}: is_active={s.get('is_active')} (type: {type(s.get('is_active'))})")
                self._last_warning_time = current_time
            
        except Exception as e:
            error_msg = str(e)
            # Check if it's the PGRST116 error (no rows found)
            if "PGRST116" in error_msg or "0 rows" in error_msg:
                if should_log_warning:
                    log.warning("sender_pool table is empty or has no active senders. Using config fallback.")
                    self._last_warning_time = current_time
            else:
                if should_log_warning:
                    log.error(f"Error querying sender_pool table: {e}")
                    self._last_warning_time = current_time
        
        # Fallback to config SMTP settings if sender_pool is empty or exhausted
        try:
            settings = config_manager.get_settings()
            smtp_config = settings.get("smtp", {})
            smtp_email = smtp_config.get("smtp_email", "")
            smtp_password = smtp_config.get("smtp_password", "")
            
            if smtp_email and smtp_password:
                if should_log_warning:
                    log.info("Using fallback SMTP credentials from config file")
                    self._last_warning_time = current_time
                result = {
                    "success": True,
                    "data": {
                        "smtp_server": smtp_config.get("smtp_server", "smtp.gmail.com"),
                        "smtp_port": int(smtp_config.get("smtp_port", 587)),
                        "smtp_email": smtp_email,
                        "smtp_password": smtp_password,
                    },
                }
                self._sender_cache = result
                self._sender_cache_time = current_time
                return result
            else:
                if should_log_warning:
                    log.warning("No SMTP credentials in config file either")
                    self._last_warning_time = current_time
        except Exception as config_error:
            if should_log_warning:
                log.error(f"Error reading config SMTP settings: {config_error}")
                self._last_warning_time = current_time
        
        # No credentials available anywhere - cache the failure too
        result = {"success": False, "error": "No SMTP sender available in database (sender_pool) or config. Please add SMTP credentials via admin panel or configure in settings."}
        self._sender_cache = result
        self._sender_cache_time = current_time
        return result

    def get_subscription_status(self):
        """
        Fetches the user's subscription status and plan features.
        Detects plan changes and updates dates accordingly.
        If plan changes, updates start date. If same plan, keeps existing dates.
        """
        if not self.current_user:
            return None # Return None, not a dict
        
        try:
            from datetime import datetime, timezone, timedelta
            
            # RLS Policy: "Allow user to read their own subscription"
            res = self.client.from_('subscriptions').select('*, plans(features, name, id)').single().execute()
            
            if res.data:
                log.info(f"Subscription status for {self.current_user.email}: {res.data['status']}")
                
                # Get current plan_id from database
                current_plan_id = res.data.get('plan_id')
                
                # Check if we have previous subscription data to compare
                previous_plan_id = None
                if self.subscription_data:
                    previous_plan_id = self.subscription_data.get('plan_id')
                
                # If plan changed (and not first time loading), update start date
                if previous_plan_id and current_plan_id and previous_plan_id != current_plan_id:
                    log.info(f"Plan changed from {previous_plan_id} to {current_plan_id}. Updating subscription dates.")
                    # Plan changed - update start date to now
                    now = datetime.now(timezone.utc)
                    # Update subscription start date (created_at) and end date
                    try:
                        # Calculate end date (30 days from now for active subscriptions)
                        if res.data['status'] == 'active':
                            new_end_date = now + timedelta(days=30)
                            update_data = {
                                'created_at': now.isoformat(),
                                'subscription_ends_at': new_end_date.isoformat(),
                                'updated_at': now.isoformat()
                            }
                            # Update in database
                            self.client.from_('subscriptions').update(update_data).eq('user_id', self.current_user.id).execute()
                            log.info(f"Updated subscription dates: start={now.isoformat()}, end={new_end_date.isoformat()}")
                            # Update local data
                            res.data['created_at'] = now.isoformat()
                            res.data['subscription_ends_at'] = new_end_date.isoformat()
                    except Exception as e:
                        log.error(f"Failed to update subscription dates: {e}")
                
                # Check if trial is expired
                if res.data['status'] == 'trialing':
                    trial_end = datetime.fromisoformat(res.data['trial_ends_at'].replace('Z', '+00:00'))
                    if trial_end < datetime.now(trial_end.tzinfo):
                        log.warning("User trial has expired.")
                        res.data['status'] = 'expired'
                
                settings = config_manager.get_settings()
                features_list = []
                
                # If user is in trial, grant all premium features
                if res.data['status'] == 'trialing':
                    # All premium features available during trial
                    features_list = [
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
                    log.info(f"User is in trial - granting all premium features: {features_list}")
                elif res.data.get('plans'):
                    features_list = res.data['plans'].get('features', [])
                
                log.info(f"Plan allows features: {features_list}")
                settings["allowed_features"] = features_list
                config_manager.update_settings(settings)
                
                self.subscription_data = res.data
                return res.data
                
            else:
                log.error(f"CRITICAL: No subscription record found for user {self.current_user.id}")
                return None
        
        except Exception as e:
            log.error(f"Get subscription exception: {e}")
            return None
            
    def get_all_plans(self):
        """Fetches all plans from the plans table."""
        try:
            res = self.client.from_('plans').select('*').execute()
            if res.data:
                return res.data
            return []
        except Exception as e:
            log.error(f"Could not fetch plans: {e}")
            return []

    def sign_out(self):
        """This is a 'soft' logout. It clears the session but keeps the token."""
        try:
            self.client.auth.sign_out()
            self.current_user = None
            self.session = None
            self.subscription_data = None
            log.info("Signed out successfully (session cleared).")
            return {"success": True}
        except Exception as e:
            log.error(f"Sign out exception: {e}")
            return {"success": False, "error": str(e)}

auth_service = AuthService()