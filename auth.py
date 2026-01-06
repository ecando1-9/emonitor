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
            
            # Step 1: Sign up the user in Supabase Auth
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
                log.info(f"Auth signup successful for {email}. Creating user record...")
                
                # Step 2: Create user record in public.users table
                try:
                    user_data = {
                        "id": res.user.id,
                        "email": email,
                        "device_hash": device_hash,
                        "created_at": "now()",
                        "updated_at": "now()"
                    }
                    
                    # Insert user record
                    insert_result = self.client.table("users").insert(user_data).execute()
                    log.info(f"User record created successfully in public.users table")
                    
                except Exception as db_error:
                    log.error(f"Failed to create user record: {db_error}")
                    log.warning("Continuing with login despite user record creation failure")
                
                # Step 3: Check app config for auto-trial creation
                try:
                    # Fetch app config settings
                    auto_trial_config = self.client.table("app_config").select("value").eq("key", "auto_create_trial").execute()
                    trial_days_config = self.client.table("app_config").select("value").eq("key", "free_trial_days").execute()
                    
                    # Check if auto-trial is enabled
                    auto_create = True  # Default
                    if auto_trial_config.data and len(auto_trial_config.data) > 0:
                        value = auto_trial_config.data[0].get("value", "true").lower()
                        auto_create = value in ["true", "1", "yes", "enabled"]
                    
                    # Get trial days
                    trial_days = 7  # Default
                    if trial_days_config.data and len(trial_days_config.data) > 0:
                        try:
                            trial_days = int(trial_days_config.data[0].get("value", "7"))
                        except:
                            trial_days = 7
                    
                    log.info(f"App config: auto_create_trial={auto_create}, trial_days={trial_days}")
                    
                    # Create trial if enabled
                    if auto_create:
                        from datetime import datetime, timedelta
                        
                        trial_end = datetime.now() + timedelta(days=trial_days)
                        
                        subscription_data = {
                            "user_id": res.user.id,
                            "plan_id": "free",
                            "status": "trialing",
                            "trial_ends_at": trial_end.isoformat(),
                            "device_hash": device_hash,
                            "created_at": "now()",
                            "updated_at": "now()"
                        }
                        
                        sub_result = self.client.table("subscriptions").insert(subscription_data).execute()
                        log.info(f"✅ Free trial created: {trial_days} days (ends {trial_end.strftime('%Y-%m-%d')})")
                    else:
                        log.info("Auto-trial disabled by admin. User will need manual subscription assignment.")
                        
                except Exception as settings_error:
                    log.warning(f"Could not read app config or create trial: {settings_error}")
                    log.info("User can still login. Subscription can be assigned via admin panel.")
                
                # Step 4: Sign in to get session
                return self.sign_in(email, password)
                
            if res.api_error:
                log.error(f"Sign up failed: {res.api_error.message}")
                return {"success": False, "error": res.api_error.message}
                
        except Exception as e:
            log.error(f"Sign up exception: {e}")
            log.error(f"Exception type: {type(e).__name__}")
            log.error(f"Exception details: {str(e)}")
            import traceback
            log.error(f"Traceback: {traceback.format_exc()}")
            if "Trial limit reached" in str(e):
                return {"success": False, "error": "Trial limit reached for this device (maximum 5 trials). Contact support."}
            if "CRITICAL" in str(e):
                return {"success": False, "error": "No available sender emails in the pool. Please contact support."}
            return {"success": False, "error": f"Signup error: {str(e)}"}

    def sign_in(self, email, password):
        """Signs in and fetches the user's subscription status."""
        try:
            from datetime import datetime, timedelta
            from device_fingerprint import get_device_hash
            
            # Check login attempts before trying to sign in
            device_hash = get_device_hash()
            ten_min_ago = (datetime.now() - timedelta(minutes=10)).isoformat()
            
            try:
                # Use RPC to check if blocked (bypass RLS read restrictions)
                result = self.client.rpc("check_is_blocked", {"p_email": email}).execute()
                
                is_blocked = result.data
                
                if is_blocked:
                    log.warning(f"Login blocked for {email}: Too many failed attempts")
                    return {
                        "success": False, 
                        "error": "Too many failed login attempts. Please wait 10 minutes and try again."
                    }
            except Exception as e:
                log.warning(f"Could not check login attempts RPC: {e}")
                # Continue even if check fails
            
            # Attempt login
            res = self.client.auth.sign_in_with_password({"email": email, "password": password})
            
            if res.user:
                # Record successful login
                # Record successful login
                try:
                    self.client.rpc("record_login_attempt", {
                        "p_email": email,
                        "p_device_hash": device_hash,
                        "p_success": True
                    }).execute()
                except Exception as ex:
                    log.warning(f"Failed to record successful login via RPC: {ex}")
                
                
                self.current_user = res.user
                self.session = res.session
                log.info(f"Sign in successful for {res.user.email}")
                
                self.save_full_login_session(res.session.refresh_token)
                
                # Track active device for single device login
                from device_fingerprint import get_device_hash
                current_device = get_device_hash()
                
                try:
                    # Check if user is logged in on different device
                    user_record = self.client.table("users").select("active_device_hash, email").eq("id", res.user.id).execute()
                    
                    if user_record.data and len(user_record.data) > 0:
                        old_device = user_record.data[0].get("active_device_hash")
                        
                        if old_device and old_device != current_device:
                            log.info(f"User {res.user.email} logging in from new device. Previous device will be logged out.")
                            log.info(f"Old device: {old_device[:8]}..., New device: {current_device[:8]}...")
                    
                    # Update active device and session
                    self.client.table("users").update({
                        "active_device_hash": current_device,
                        "active_session_id": res.session.access_token,
                        "last_active": "now()",
                        "last_login": "now()"
                    }).eq("id", res.user.id).execute()
                    
                    log.info(f"Active device updated for user {res.user.email}")
                    
                    # --- NEW: Update Devices Table for Admin Monitoring ---
                    try:
                        # Register/Update device in devices table
                        # This enables "Multi-Device Monitoring" in admin panel
                        self.client.table("devices").upsert({
                            "device_hash": current_device,
                            "last_user_id": res.user.id,
                            "last_seen": "now()",
                            "is_blocked": False
                        }, on_conflict="device_hash").execute()
                    except Exception as dev_e:
                        log.warning(f"Could not update devices table: {dev_e}")
                    # ------------------------------------------------------
                    
                except Exception as e:
                    log.warning(f"Could not update active device: {e}")
                    # Continue with login even if device tracking fails
                
                # Load user-specific settings from database
                from config import config_manager
                config_manager.load_user_settings_from_db(res.user.id, self.client)
                log.info("User-specific settings loaded")
                
                # --- !! NEW: FETCH SUBSCRIPTION !! ---
                sub_data = self.get_subscription_status()
                # For new users, subscription may not exist yet - that's okay
                if sub_data is None:
                    log.warning("No subscription found for user. Using default/trial features.")
                    sub_data = {"status": "new_user", "plan_id": None}
                
                return {"success": True, "user": res.user, "subscription": sub_data}
                
            if res.api_error:
                # Record failed login attempt
                from datetime import datetime
                from device_fingerprint import get_device_hash
                try:
                    device_hash = get_device_hash()
                    # Use RPC to bypass RLS issues
                    self.client.rpc("record_login_attempt", {
                        "p_email": email,
                        "p_device_hash": device_hash,
                        "p_success": False
                    }).execute()
                except Exception as ex:
                    log.warning(f"Failed to record login attempt via RPC: {ex}")
                
                log.error(f"Sign in failed: {res.api_error.message}")
                return {"success": False, "error": res.api_error.message}
        except Exception as e:
            # Record failed login attempt for exceptions too
            from datetime import datetime
            from device_fingerprint import get_device_hash
            try:
                device_hash = get_device_hash()
                # Use RPC to bypass RLS issues
                self.client.rpc("record_login_attempt", {
                    "p_email": email,
                    "p_device_hash": device_hash,
                    "p_success": False
                }).execute()
            except Exception as ex:
                log.warning(f"Failed to record login attempt via RPC: {ex}")
            
            log.error(f"Sign in exception: {e}")
            return {"success": False, "error": str(e)}
    
    def check_active_device(self):
        """
        Check if current device is still the active device for this user.
        Returns True if active, False if user logged in on another device.
        """
        if not self.current_user:
            return True  # No user logged in, nothing to check
        
        try:
            from device_fingerprint import get_device_hash
            current_device = get_device_hash()
            
            # Get active device from database
            user_record = self.client.table("users").select("active_device_hash").eq("id", self.current_user.id).execute()
            
            if user_record.data and len(user_record.data) > 0:
                active_device = user_record.data[0].get("active_device_hash")
                
                if active_device and active_device != current_device:
                    log.warning(f"User {self.current_user.email} is active on different device. Current: {current_device[:8]}..., Active: {active_device[:8]}...")
                    return False
            
            return True
            
        except Exception as e:
            log.error(f"Error checking active device: {e}")
            return True  # On error, don't force logout

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
            # Reverting to simple call first as 'redirect_to' kwarg failed
            # If the link is still empty, we will try passing options dict next
            self.client.auth.reset_password_for_email(email)
            log.info(f"Password reset email sent to {email}")
            return {"success": True}
        except Exception as e:
            log.error(f"Password reset exception: {e}")
            return {"success": False, "error": str(e)}

    def clear_sender_cache(self):
        """Clear the sender assignment cache to force a fresh lookup"""
        self._sender_cache = None
        self._sender_cache_time = 0
        log.debug("Sender cache cleared")
    
    def get_sender_assignment(self, use_cache=True):
        """Fetch SMTP sender credentials for the current user from sender_pool database table.

        Queries the sender_pool table to get an active sender with the lowest assigned_count.
        This keeps all sensitive credentials only in the database, not hard-coded in the app.
        
        Falls back to config SMTP settings if sender_pool is empty or has no active senders.
        
        Uses caching to avoid repeated database queries and log spam.
        """
        if not self.current_user:
            # Try to use emergency fallback RPC (allows sending alerts even if logged out)
            try:
                log.info("User not logged in - attempting to fetch emergency sender via secure RPC...")
                rpc_response = self.client.rpc("get_emergency_sender_secure").execute()
                if rpc_response.data:
                    data = rpc_response.data
                    result = {
                        "success": True,
                        "data": {
                            "smtp_server": data.get("smtp_server"),
                            "smtp_port": int(data.get("smtp_port", 587)),
                            "smtp_email": data.get("smtp_email"),
                            "smtp_password": data.get("smtp_password"),
                        }
                    }
                    log.info(f"✅ Retrieved emergency sender via RPC: {data.get('smtp_email')}")
                    return result
            except Exception as rpc_error:
                log.warning(f"Failed to get emergency sender via RPC: {rpc_error}")
            
            return {"success": False, "error": "User not logged in"}

        # Check cache first (if enabled and not expired)
        # But if cache contains a failure, always retry to get fresh data
        current_time = time.time()
        if use_cache and self._sender_cache:
            # If cache is a success, use it if not expired
            if self._sender_cache.get("success") and (current_time - self._sender_cache_time) < self._sender_cache_ttl:
                return self._sender_cache
            # If cache is a failure, clear it and retry (in case sender was just activated)
            elif not self._sender_cache.get("success"):
                log.debug("Clearing failed sender cache to retry...")
                self._sender_cache = None

        # Throttle warning messages (only log once per 5 minutes)
        should_log_warning = (current_time - self._last_warning_time) >= self._warning_throttle

        try:
            # Query sender_pool table from database - get active senders ordered by assigned_count
            log.debug("Querying sender_pool table from database...")
            
            # Query for active senders using WHERE clause (is_active = true)
            # This is much simpler and faster than filtering in Python
            try:
                active_senders_query = (
                    self.client
                    .from_("sender_pool")
                    .select("id, smtp_email, smtp_server, smtp_port, smtp_password, is_active, assigned_count, max_users")
                    .eq("is_active", True)  # Only get senders where is_active = true
                    .order("assigned_count", desc=False)  # Sort by lowest assigned_count
                    .execute()
                )
                res_data = active_senders_query.data if active_senders_query.data else []
                
                if res_data:
                    log.info(f"✅ Found {len(res_data)} active sender(s) in database")
                    for sender in res_data:
                        log.info(f"  - {sender.get('smtp_email')}: assigned_count={sender.get('assigned_count')}, max_users={sender.get('max_users')}")
                else:
                    log.error("❌ No active sender found in sender_pool database table (is_active = true)")
                    # Debug: Check if there are ANY senders at all
                    try:
                        all_senders = (
                            self.client
                            .from_("sender_pool")
                            .select("id, smtp_email, is_active")
                            .limit(10)
                            .execute()
                        )
                        if all_senders.data:
                            log.error(f"Found {len(all_senders.data)} sender(s) in pool, but NONE have is_active=true:")
                            for s in all_senders.data:
                                log.error(f"  - {s.get('smtp_email')}: is_active={s.get('is_active')}")
                        else:
                            log.error("❌ sender_pool table is EMPTY - no senders found at all!")
                    except Exception as debug_error:
                        log.error(f"Error during debug query: {debug_error}")
            
            except Exception as e:
                log.error(f"Error querying active senders: {e}")
                res_data = []
            
            # Check if we got any data from the database
            if res_data and len(res_data) > 0:
                log.info(f"✅ Found active sender in database: {res_data[0].get('smtp_email')}")
                row = res_data[0]
                sender_id = row.get("id")
                
                if should_log_warning:
                    log.info(f"Found active sender in sender_pool: {row.get('smtp_email')} (ID: {sender_id})")
                
                # Check if sender has reached max_users limit
                max_users = row.get("max_users", 100)
                assigned_count = row.get("assigned_count", 0)
                
                if max_users is not None and assigned_count is not None and assigned_count >= max_users:
                    if should_log_warning:
                        log.warning(f"Sender {row.get('smtp_email')} has reached max_users limit ({assigned_count}/{max_users}). Trying next sender...")
                    # Try to find another sender - query for next best alternative
                    try:
                        alternative_query = (
                            self.client
                            .from_("sender_pool")
                            .select("id, smtp_email, smtp_server, smtp_port, smtp_password, is_active, assigned_count, max_users")
                            .eq("is_active", True)
                            .neq("id", sender_id)  # Exclude current sender
                            .order("assigned_count", desc=False)
                            .limit(1)
                            .execute()
                        )
                        if alternative_query.data:
                            row = alternative_query.data[0]
                            sender_id = row.get("id")
                            if should_log_warning:
                                log.info(f"Using alternative sender: {row.get('smtp_email')} (ID: {sender_id})")
                        else:
                            if should_log_warning:
                                log.warning("No alternative active sender found. Falling back to config SMTP.")
                            row = None
                    except Exception as alt_error:
                        log.error(f"Error querying alternative senders: {alt_error}")
                        row = None
                
                if row:
                    # Increment assigned_count in database (optional - can be done asynchronously)
                    try:
                        if sender_id:
                            self.client.rpc("increment_sender_assigned_count", {
                                "sender_id_to_inc": sender_id
                            }).execute()
                            log.debug(f"Incremented assigned_count for sender {sender_id} via RPC")
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
                log.error("❌ No active sender found in sender_pool database table. Checking config fallback...")
                # Debug: Check if there are any senders at all
                try:
                    debug_res = (
                        self.client
                        .from_("sender_pool")
                        .select("id, smtp_email, is_active")
                        .limit(5)
                        .execute()
                    )
                    if debug_res.data:
                        log.error(f"Found {len(debug_res.data)} sender(s) in pool, but none are active:")
                        for s in debug_res.data:
                            is_active_val = s.get('is_active')
                            log.error(f"  - {s.get('smtp_email')}: is_active={is_active_val} (type: {type(is_active_val)}, repr: {repr(is_active_val)})")
                            # Show what the check would do
                            if is_active_val is None:
                                log.error(f"    -> Would be treated as ACTIVE (NULL = active for backward compatibility)")
                            elif isinstance(is_active_val, bool):
                                log.error(f"    -> Boolean check: {is_active_val}")
                            else:
                                cleaned = str(is_active_val).strip().lower()
                                would_be_active = cleaned in ['true', '1', 'yes', 'active', 't', 'enabled', 'on']
                                log.error(f"    -> String check: '{cleaned}' -> Would be active: {would_be_active}")
                    else:
                        log.error("❌ sender_pool table is EMPTY - no senders found at all!")
                except Exception as debug_error:
                    log.error(f"Error during debug query: {debug_error}")
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