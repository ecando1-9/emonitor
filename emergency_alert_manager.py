import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import threading
import time
import json
import os
from datetime import datetime
from logger_setup import log
from config import config_manager
from auth import auth_service
from device_fingerprint import get_device_hash
from capture.telemetry import get_location_info_data
from capture.activity import get_active_window_data, get_comprehensive_activity_summary
from timezone_utils import get_local_timestamp_iso

EMERGENCY_EMAIL = "ecando976@gmail.com"
EMERGENCY_QUEUE_FILE = "emergency_queue.json"
MAX_RETRIES = 5
RETRY_DELAYS = [1, 2, 5, 10, 30]  # Exponential backoff in seconds

# Global state for emergency mode
_emergency_active = False
_current_alert_id = None
_emergency_stop_event = threading.Event()
_last_smtp_warning_time = 0  # Throttle SMTP warnings
_smtp_warning_throttle = 300  # Only warn once per 5 minutes
_original_features = None  # Store original features to restore when stopping
# Callbacks to notify UI about emergency state changes
_state_change_callbacks = []
_emergency_file_buffer = []
_buffer_lock = threading.Lock()
_current_sender_config = None  # Pin sender for the session

def register_state_change_callback(cb):
    try:
        if cb not in _state_change_callbacks:
            _state_change_callbacks.append(cb)
    except Exception:
        pass

def unregister_state_change_callback(cb):
    try:
        if cb in _state_change_callbacks:
            _state_change_callbacks.remove(cb)
    except Exception:
        pass

def _notify_state_change():
    try:
        for cb in list(_state_change_callbacks):
            try:
                cb()
            except Exception:
                pass
    except Exception:
        pass

def get_emergency_data():
    """Gathers all available data for emergency alert."""
    log.info("=== GATHERING EMERGENCY DATA ===")
    data = {
        "timestamp": datetime.now().isoformat(),
        "device_id": get_device_hash(),
    }
    
    # Get user info from current_user and settings - ensure all fields are populated
    try:
        settings = config_manager.get_settings()
        emergency_settings = settings.get("emergency", {})
        user_settings = settings.get("user", {})
        
        # Log what we found in settings
        log.info(f"Settings emergency section: {emergency_settings}")
        log.info(f"Settings user section: {user_settings}")
        
        if auth_service.current_user:
            # Get email from current user
            data["user_email"] = auth_service.current_user.email or "Unknown"
            log.info(f"User email from auth: {data['user_email']}")
            
            # Try to get name from multiple sources
            user_metadata = getattr(auth_service.current_user, 'user_metadata', {}) or {}
            raw_metadata = getattr(auth_service.current_user, 'raw_user_meta_data', {}) or {}
            
            # Check settings for user name (from emergency settings) - prioritize this
            settings_name = emergency_settings.get("user_name", "")
            if settings_name:
                settings_name = str(settings_name).strip()
            log.info(f"User name from emergency settings: '{settings_name}'")
            
            name = (settings_name if settings_name else  # First check settings
                   user_metadata.get('name') or 
                   raw_metadata.get('name') or 
                   user_metadata.get('full_name') or
                   raw_metadata.get('full_name') or
                   (auth_service.current_user.email.split('@')[0] if auth_service.current_user.email else "Unknown User"))  # Fallback to email username
            data["user_name"] = name if name else "Unknown User"
            log.info(f"Final user_name: '{data['user_name']}'")
        else:
            # If not logged in, try to get from settings
            data["user_email"] = settings.get("user", {}).get("recipient_email", "Unknown")
            data["user_name"] = emergency_settings.get("user_name", "Unknown User")
            if not data["user_name"] or data["user_name"] == "":
                data["user_name"] = "Unknown User"
            log.info(f"Not logged in - using settings: name='{data['user_name']}', email='{data['user_email']}'")
    except Exception as e:
        log.error(f"Failed to get user info: {e}")
        import traceback
        log.error(traceback.format_exc())
        data["user_email"] = "Unknown"
        data["user_name"] = "Unknown User"
    
    # Get location
    try:
        location_data = get_location_info_data()
        data["location"] = location_data
    except Exception as e:
        log.error(f"Failed to get location: {e}")
        data["location"] = "Not available"
    
    # Get activity summary
    try:
        activity_summary = get_active_window_data()
        data["recent_activity"] = activity_summary
    except Exception as e:
        log.error(f"Failed to get activity: {e}")
        data["recent_activity"] = "Not available"
    
    # Get device name - ensure it's not empty
    try:
        settings = config_manager.get_settings()
        device_name_raw = settings.get("user", {}).get("device_name", "")
        if device_name_raw:
            device_name = str(device_name_raw).strip()
        else:
            device_name = ""
        data["device_name"] = device_name if device_name else "Unknown Device"
        log.info(f"Device name from settings: '{device_name}' -> Final: '{data['device_name']}'")
    except Exception as e:
        log.error(f"Failed to get device name: {e}")
        import traceback
        log.error(traceback.format_exc())
        data["device_name"] = "Unknown Device"
    
    # Get emergency contacts and user phone - ensure all fields are populated
    try:
        settings = config_manager.get_settings()
        emergency_settings = settings.get("emergency", {})
        
        # Get user phone - ensure it's not None
        user_phone_raw = emergency_settings.get("user_phone", "")
        if user_phone_raw:
            user_phone = str(user_phone_raw).strip()
        else:
            user_phone = ""
        data["user_phone"] = user_phone
        log.info(f"User phone from settings: '{user_phone}'")
        
        # Get user emergency email - ensure it's not None
        emergency_email_raw = emergency_settings.get("emergency_email", "")
        if emergency_email_raw:
            emergency_email = str(emergency_email_raw).strip()
        else:
            emergency_email = ""
        data["emergency_email"] = emergency_email
        log.info(f"User emergency email from settings: '{emergency_email}'")
        
        # Handle both old format (list of strings) and new format (list of dicts with name/phone)
        contacts_raw = emergency_settings.get("emergency_contacts", [])
        log.info(f"Emergency contacts raw from settings: {contacts_raw}")
        emergency_contacts = []
        for contact in contacts_raw:
            if isinstance(contact, dict):
                # New format: {"name": "...", "phone": "..."}
                emergency_contacts.append(contact)
            else:
                # Old format: just phone number string
                emergency_contacts.append({"name": "", "phone": str(contact)})
        data["emergency_contacts"] = emergency_contacts if emergency_contacts else []
        log.info(f"Final emergency_contacts: {data['emergency_contacts']}")
    except Exception as e:
        log.error("Failed to get emergency contacts and email")
        log.debug(f"Error details: {e}")
        import traceback
        log.debug(traceback.format_exc())
        data["user_phone"] = ""
        data["emergency_email"] = ""
        data["emergency_contacts"] = []
    
    log.info("=== FINAL EMERGENCY DATA ===")
    log.info(f"  user_name: '{data.get('user_name')}'")
    log.info(f"  user_email: '{data.get('user_email')}'")
    log.info(f"  user_phone: '{data.get('user_phone')}'")
    log.info(f"  emergency_email: '{data.get('emergency_email')}'")
    log.info(f"  device_name: '{data.get('device_name')}'")
    log.info(f"  emergency_contacts: {data.get('emergency_contacts')}")
    log.info("=== END EMERGENCY DATA ===\n")
    
    return data

def format_emergency_email_body(data, for_emergency_contact=False, data_sharing_prefs=None):
    """
    Formats the emergency alert email body.
    
    Args:
        data: Emergency data dictionary
        for_emergency_contact: If True, only include data the user chose to share
        data_sharing_prefs: Dictionary of data sharing preferences for emergency contacts
    """
    # If sending to emergency contact, filter data based on preferences
    if for_emergency_contact and data_sharing_prefs:
        log.info(f"Filtering emergency contact email - Data sharing preferences: {data_sharing_prefs}")
        body_parts = []
        
        body_parts.append("EMERGENCY ALERT - IMMEDIATE ACTION REQUIRED\n\n")
        body_parts.append(f"User: {data.get('user_name', 'Unknown')}\n")
        body_parts.append(f"Email: {data.get('user_email', 'Unknown')}\n")
        body_parts.append(f"Timestamp: {data.get('timestamp', 'Unknown')}\n")
        
        if data_sharing_prefs.get('device_info', False):
            body_parts.append(f"\nDevice Information:\n")
            body_parts.append(f"- Device Name: {data.get('device_name', 'Unknown')}\n")
            body_parts.append(f"- Device ID: {data.get('device_id', 'Unknown')}\n")
        
        if data_sharing_prefs.get('last_location', False):
            body_parts.append(f"\nLocation Information:\n")
            location = data.get('location', 'Not available')
            if isinstance(location, dict):
                body_parts.append(json.dumps(location, indent=2) + "\n")
            else:
                body_parts.append(str(location) + "\n")
        
        if data_sharing_prefs.get('activity_summary', False):
            body_parts.append(f"\nRecent Activity:\n")
            activity = data.get('recent_activity', 'Not available')
            body_parts.append(str(activity) + "\n")
        
        # Get email interval from settings for display
        settings = config_manager.get_settings()
        email_interval_seconds = settings.get("emergency", {}).get("email_interval_seconds", 30)
        
        # Format interval for display
        if email_interval_seconds < 60:
            interval_text = f"{email_interval_seconds} seconds"
        elif email_interval_seconds == 60:
            interval_text = "1 minute"
        elif email_interval_seconds % 60 == 0:
            minutes = email_interval_seconds // 60
            interval_text = f"{minutes} minutes"
        else:
            minutes = email_interval_seconds // 60
            seconds = email_interval_seconds % 60
            interval_text = f"{minutes}m {seconds}s"
        
        # Note: Initial alert doesn't include file attachments
        # Files will be sent in periodic updates at user-configured interval
        body_parts.append(f"\n📎 DATA CAPTURE STATUS:\n")
        if data_sharing_prefs.get('screenshot', False):
            body_parts.append(f"✓ Screenshots: Will be sent in periodic updates (every {interval_text})\n")
        if data_sharing_prefs.get('camera', False):
            body_parts.append(f"✓ Camera: Will be sent in periodic updates (every {interval_text})\n")
        if data_sharing_prefs.get('microphone', False):
            body_parts.append(f"✓ Microphone: Will be sent in periodic updates (every {interval_text})\n")
        if data_sharing_prefs.get('screen_record', False):
            body_parts.append(f"✓ Screen Recording: Will be sent in periodic updates (every {interval_text})\n")
        
        body_parts.append("\n--- Emergency Contact Notification ---\n")
        body_parts.append("This is an automated emergency notification. Please contact the user or emergency services if needed.\n")
        
        body = "".join(body_parts)
    else:
        # Full body for admin (always gets all data)
        body = f"""
EMERGENCY ALERT - IMMEDIATE ACTION REQUIRED

Device Information:
- Device ID: {data.get('device_id', 'Unknown')}
- Device Name: {data.get('device_name', 'Unknown')}
- Timestamp: {data.get('timestamp', 'Unknown')}

Location Information:
{json.dumps(data.get('location', 'Not available'), indent=2)}

Recent Activity:
{data.get('recent_activity', 'Not available')}

Captured Data Clips:
"""
        # List what data was captured based on user preferences
        data_sharing = data.get('data_shared', {})
        captured_items = []
        if data_sharing.get('screenshot', False):
            captured_items.append("- Screenshot")
        if data_sharing.get('camera', False):
            captured_items.append("- Camera video (30 sec with audio)")
        if data_sharing.get('microphone', False):
            captured_items.append("- Microphone audio (30 sec)")
        if data_sharing.get('screen_record', False):
            captured_items.append("- Screen recording (30 sec)")
        if data_sharing.get('activity_summary', False):
            captured_items.append("- Activity summary")
        if data_sharing.get('device_info', False) or data_sharing.get('last_location', False):
            captured_items.append("- Device info and location")
        
        if captured_items:
            body += "\n".join(captured_items)
        else:
            body += "\n- No data captured (user preferences disabled all captures)"
        
        body += "\n\nAll captured data clips are attached to this email or sent separately."
        body += f"\n- Screenshot: {data.get('data_shared', {}).get('screenshot', False)}"
        body += f"\n- Device Info: {data.get('data_shared', {}).get('device_info', False)}"
        body += f"\n- Location: {data.get('data_shared', {}).get('last_location', False)}"
        body += f"\n- Activity: {data.get('data_shared', {}).get('activity_summary', False)}"
        body += f"\n- Logs: {data.get('data_shared', {}).get('logs', False)}"
        body += f"\n- Camera Capture: {data.get('data_shared', {}).get('camera', False)}"
        body += f"\n- Microphone Capture: {data.get('data_shared', {}).get('microphone', False)}"
        body += f"\n- Screen Recording: {data.get('data_shared', {}).get('screen_record', False)}"

    return body

def check_smtp_configuration():
    """Diagnostic function to check SMTP configuration and log details"""
    log.info("=== EMERGENCY EMAIL CONFIGURATION CHECK ===")
    
    # Check sender_pool
    try:
        if auth_service.current_user:
            all_senders = auth_service.client.from_("sender_pool").select("*").execute()
            if all_senders.data:
                log.info(f"Found {len(all_senders.data)} sender(s) in sender_pool:")
                for s in all_senders.data:
                    is_active = s.get('is_active')
                    log.info(f"  - {s.get('smtp_email')}: is_active={is_active} (type: {type(is_active).__name__})")
            else:
                log.warning("sender_pool table is EMPTY - no senders found")
        else:
            log.warning("User not logged in - cannot check sender_pool")
    except Exception as e:
        log.error(f"Error checking sender_pool: {e}")
    
    # Check config fallback
    try:
        settings = config_manager.get_settings()
        smtp_config = settings.get("smtp", {})
        smtp_email = smtp_config.get("smtp_email", "")
        smtp_password = smtp_config.get("smtp_password", "")
        
        if smtp_email and smtp_password:
            log.info(f"Config fallback SMTP found: {smtp_email}")
        else:
            log.warning("Config fallback SMTP is NOT configured (smtp_email or smtp_password is empty)")
    except Exception as e:
        log.error(f"Error checking config SMTP: {e}")
    
    log.info("=== END CONFIGURATION CHECK ===")

def send_emergency_email(data, retry_count=0, alert_id=None):
    """Sends emergency alert email with retry logic.
    
    Uses sender_pool from database first, falls back to config SMTP if pool is empty.
    
    Args:
        data: Emergency data dictionary
        retry_count: Number of retry attempts (default 0)
        alert_id: Optional alert ID to update database flags when email is sent
    
    Returns False if email cannot be sent (no SMTP credentials).
    This is not a critical failure - the alert is still saved to database.
    """
    try:
        # Run diagnostic check on first attempt
        if retry_count == 0:
            check_smtp_configuration()
        
        # Get sender credentials from sender_pool (or config fallback)
        # Use use_cache=False for emergency to ensure we get a fresh sender if available
        log.info("EMERGENCY: Attempting to get SMTP sender credentials...")
        creds_result = auth_service.get_sender_assignment(use_cache=False)
        
        if not creds_result.get("success"):
            error_msg = creds_result.get("error", "Unknown error")
            log.error(f"EMERGENCY: Failed to get SMTP credentials - {error_msg}")
            log.error("EMERGENCY: Email cannot be sent. Alert is still saved to database.")
            log.error("EMERGENCY: To fix: Add SMTP credentials via admin panel (sender_pool table) or configure in settings.json")
            return False
        
        sender_config = creds_result.get("data")
        if not sender_config:
            log.error("EMERGENCY: Sender config data is empty - email will not be sent.")
            log.error("EMERGENCY: Check sender_pool table in database or config SMTP settings")
            return False
        
        # Log which sender is being used (for debugging)
        log.info(f"Using SMTP sender: {sender_config.get('smtp_email', 'Unknown')} from sender_pool")
        
        # Get recipient email and emergency email from settings
        # DO NOT send to admin email - only send to recipient email and emergency email
        settings = config_manager.get_settings()
        emergency_settings = settings.get("emergency", {})
        user_email = settings.get("user", {}).get("recipient_email", "")
        emergency_email_user = emergency_settings.get("emergency_email", "")
        
        # Only send to recipient email and emergency email (NOT admin email, NOT hardcoded EMERGENCY_EMAIL)
        recipients = []
        if user_email:
            cleaned_email = user_email.strip()
            if cleaned_email:
                recipients.append(cleaned_email)
        if emergency_email_user:
            cleaned_emerg = emergency_email_user.strip()
            if cleaned_emerg and cleaned_emerg not in recipients:
                recipients.append(cleaned_emerg)
        
        if not recipients:
            log.error("EMERGENCY: No recipient email or emergency email configured. Cannot send email.")
            return False
        
        # Create email
        msg = MIMEMultipart()
        msg['From'] = sender_config['smtp_email']
        msg['To'] = ", ".join(recipients)
        user_name = data.get('user_name', data.get('user_email', 'Unknown'))
        msg['Subject'] = "EMERGENCY ALERT - Immediate Action Required"
        msg.attach(MIMEText(format_emergency_email_body(data), 'plain'))
        
        # Validate sender config has all required fields
        required_fields = ['smtp_server', 'smtp_port', 'smtp_email', 'smtp_password']
        missing_fields = [field for field in required_fields if not sender_config.get(field)]
        if missing_fields:
            log.error(f"Sender config missing required fields: {missing_fields}")
            return False
        
        # Send email
        log.info(f"EMERGENCY: Attempting to send email to {recipients} using {sender_config['smtp_email']} (attempt {retry_count + 1})...")
        log.info(f"EMERGENCY: SMTP Server: {sender_config['smtp_server']}:{sender_config['smtp_port']}")
        try:
            context = ssl.create_default_context()
            smtp_port = int(sender_config['smtp_port'])
            
            log.info(f"EMERGENCY: Connecting to SMTP server {sender_config['smtp_server']}:{smtp_port}...")
            with smtplib.SMTP(sender_config['smtp_server'], smtp_port, timeout=30) as server:
                log.info("EMERGENCY: Starting TLS...")
                server.starttls(context=context)
                log.info(f"EMERGENCY: Logging in as {sender_config['smtp_email']}...")
                server.login(sender_config['smtp_email'], sender_config['smtp_password'])
                log.info(f"EMERGENCY: Sending email to {recipients}...")
                server.sendmail(sender_config['smtp_email'], recipients, msg.as_string())
            
            log.info(f"EMERGENCY: ✅ Successfully sent email to {recipients} using {sender_config['smtp_email']}")
            
            # Update database flags and email_details if alert_id is provided
            if alert_id:
                try:
                    # Build email_details summary to store in DB
                    email_details_update = {
                        "last_sent_at": get_local_timestamp_iso(),
                        "recipients": recipients,
                        "subject": msg['Subject'] if 'Subject' in msg else None,
                        "sender": sender_config.get('smtp_email')
                    }

                    # Prepare email status update
                    email_status = {
                        "email_details": email_details_update
                    }
                    
                    # Determine which flags to update based on recipients
                    if EMERGENCY_EMAIL in recipients:
                        email_status["email_sent_to_admin"] = True
                        email_status["email_sent_to_admin_at"] = get_local_timestamp_iso()

                    if user_email and user_email in recipients:
                        email_status["email_sent_to_user"] = True
                        email_status["email_sent_to_user_at"] = get_local_timestamp_iso()

                    # Update using secure RPC function
                    auth_service.client.rpc("update_emergency_email_status", {
                        "alert_id": alert_id,
                        "email_status": email_status
                    }).execute()
                    log.info(f"EMERGENCY: Updated email status in database for alert #{alert_id}")
                except Exception as flag_error:
                    error_str = str(flag_error)
                    if "permission denied" in error_str.lower():
                        # Throttle permission denied logs
                        global _last_permission_denied_log
                        if not hasattr(__import__('emergency_alert_manager'), '_last_permission_denied_log') or time.time() - _last_permission_denied_log > 60:
                             log.warning(f"EMERGENCY: Database permission denied when updating flags. RLS policies likely need fix. Error: {flag_error}")
                             _last_permission_denied_log = time.time()
                    else:
                        log.warning(f"EMERGENCY: Failed to update email status: {flag_error}")
                    import traceback
                    log.debug(traceback.format_exc())
            
            return True
        except smtplib.SMTPAuthenticationError as auth_error:
            log.error(f"EMERGENCY: ❌ SMTP authentication failed for {sender_config['smtp_email']}: {auth_error}")
            log.error(f"EMERGENCY: Check if email/password is correct in sender_pool table")
            return False
        except smtplib.SMTPException as smtp_error:
            log.error(f"EMERGENCY: ❌ SMTP error sending email: {smtp_error}")
            import traceback
            log.error(traceback.format_exc())
            return False
        except Exception as e:
            log.error(f"EMERGENCY: ❌ Unexpected error sending email: {e}")
            import traceback
            log.error(traceback.format_exc())
            return False
        
    except Exception as e:
        log.error(f"Failed to send emergency email (attempt {retry_count + 1}): {e}")
        return False

def queue_emergency_alert(data):
    """Queues emergency alert for later sending if offline."""
    try:
        queue = []
        if os.path.exists(EMERGENCY_QUEUE_FILE):
            with open(EMERGENCY_QUEUE_FILE, 'r') as f:
                queue = json.load(f)
        
        queue.append({
            "data": data,
            "queued_at": datetime.now().isoformat(),
            "retry_count": 0
        })
        
        with open(EMERGENCY_QUEUE_FILE, 'w') as f:
            json.dump(queue, f, indent=2)
        
        log.info("Emergency alert queued for later sending")
        return True
    except Exception as e:
        log.error(f"Failed to queue emergency alert: {e}")
        return False

def process_emergency_queue():
    """Processes queued emergency alerts."""
    if not os.path.exists(EMERGENCY_QUEUE_FILE):
        return
    
    try:
        with open(EMERGENCY_QUEUE_FILE, 'r') as f:
            queue = json.load(f)
        
        if not queue:
            return
        
        remaining_queue = []
        for item in queue:
            data = item["data"]
            retry_count = item.get("retry_count", 0)
            
            if retry_count >= MAX_RETRIES:
                log.error(f"Emergency alert exceeded max retries. Giving up.")
                continue
            
            success = send_emergency_email(data, retry_count)
            if success:
                log.info("Successfully sent queued emergency alert")
            else:
                # Retry later
                item["retry_count"] = retry_count + 1
                remaining_queue.append(item)
        
        # Save remaining queue
        with open(EMERGENCY_QUEUE_FILE, 'w') as f:
            json.dump(remaining_queue, f, indent=2)
            
    except Exception as e:
        log.error(f"Error processing emergency queue: {e}")

def send_emergency_alert_with_retry(data, alert_id=None):
    """Sends emergency alert with retry logic and queue fallback.
    
    Args:
        data: Emergency data dictionary
        alert_id: Optional alert ID to update database flags when email is sent
    
    Returns True if email was sent successfully, False otherwise.
    Note: Even if email fails, the alert is still saved to Supabase database.
    """
    # Try immediate send
    success = send_emergency_email(data, 0, alert_id=alert_id)
    
    if not success:
        # Queue for later
        log.warning("Failed to send emergency email immediately. Queueing for retry...")
        queue_emergency_alert(data)
        # Start background retry thread
        threading.Thread(target=retry_emergency_send, args=(data,), daemon=True).start()
        # Return False but don't fail the entire alert - database save already succeeded
        return False
    
    return success

def retry_emergency_send(data, retry_count=0):
    """Retries sending emergency alert with exponential backoff."""
    if retry_count >= MAX_RETRIES:
        log.error("Emergency alert failed after all retries")
        return
    
    delay = RETRY_DELAYS[min(retry_count, len(RETRY_DELAYS) - 1)]
    log.info(f"Retrying emergency alert in {delay} seconds (attempt {retry_count + 1}/{MAX_RETRIES})...")
    time.sleep(delay)
    
    success = send_emergency_email(data, retry_count)
    if not success:
        # Retry again
        threading.Thread(target=retry_emergency_send, args=(data, retry_count + 1), daemon=True).start()
    else:
        log.info("Emergency alert sent successfully after retry")

def log_emergency_event(data, activation_method="unknown", acknowledged=False, admin_name=""):
    """Logs emergency event to audit trail."""
    try:
        log_file = "emergency_audit.log"
        event = {
            "timestamp": datetime.now().isoformat(),
            "device_id": data.get("device_id"),
            "user_email": data.get("user_email"),
            "activation_method": activation_method,
            "acknowledged": acknowledged,
            "admin_name": admin_name,
            "location": data.get("location"),
            "activity": data.get("recent_activity")
        }
        
        with open(log_file, 'a') as f:
            f.write(json.dumps(event) + "\n")
        
        log.info(f"Emergency event logged: {activation_method}")
    except Exception as e:
        log.error(f"Failed to log emergency event: {e}")

def enable_all_features_for_emergency():
    """Temporarily enables all features regardless of subscription for emergency data collection."""
    settings = config_manager.get_settings()
    
    # Save original allowed_features
    original_features = settings.get("allowed_features", [])
    settings["_emergency_original_features"] = original_features
    # Try to enable features based on the user's emergency data sharing preferences.
    # If no preferences are configured, fall back to enabling all features.
    prefs = settings.get("emergency", {}).get("data_sharing_preferences", None)
    if prefs and isinstance(prefs, dict):
        feature_map = {
            'screenshot': 'SCREENSHOT',
            'device_info': 'TELEMETRY',
            'last_location': 'TELEMETRY',
            'activity_summary': 'ACTIVITY_SUMMARY',
            'camera': 'CAMERA',
            'microphone': 'MICROPHONE',
            'screen_record': 'SCREEN_RECORD',
            'logs': 'REPORT_SCHEDULE'
        }
        new_features = set()
        # Always include telemetry if any location/device info requested
        for key, enabled in prefs.items():
            if enabled:
                mapped = feature_map.get(key)
                if mapped:
                    new_features.add(mapped)

        # If none of the preferences resulted in any feature, fall back to enabling all
        if not new_features:
            new_features = {
                "SCREENSHOT", "TELEMETRY", "ACTIVITY_SUMMARY", "ADVANCED_ACTIVITY",
                "TYPING_INTENSITY", "SCREEN_RECORD", "CAMERA", "MICROPHONE", "REPORT_SCHEDULE"
            }
    else:
        # No preferences found - enable everything
        new_features = {
            "SCREENSHOT", "TELEMETRY", "ACTIVITY_SUMMARY", "ADVANCED_ACTIVITY",
            "TYPING_INTENSITY", "SCREEN_RECORD", "CAMERA", "MICROPHONE", "REPORT_SCHEDULE"
        }

    settings["allowed_features"] = list(new_features)
    config_manager.update_settings(settings)
    log.info(f"EMERGENCY MODE: Enabled features for emergency: {settings['allowed_features']}")
    return original_features

def restore_original_features(original_features):
    """Restores original allowed_features after emergency."""
    settings = config_manager.get_settings()
    settings["allowed_features"] = original_features
    if "_emergency_original_features" in settings:
        del settings["_emergency_original_features"]
    config_manager.update_settings(settings)
    log.info("EMERGENCY MODE: Restored original feature permissions")

def cancel_running_features():
    """Cancels any running features to avoid conflicts during emergency."""
    log.warning("EMERGENCY: Cancelling all running features...")
    try:
        from scheduler import (
            CAMERA_IN_USE, MIC_IN_USE, SCREEN_REC_IN_USE, TYPED_ACTIVITY_IN_USE,
            schedule
        )
        
        # Try to stop scheduler if running (import from dashboard module)
        try:
            import sys
            # Get scheduler_thread from dashboard_ui module if available
            dashboard_module = sys.modules.get('ui.dashboard_ui')
            if dashboard_module and hasattr(dashboard_module, 'scheduler_thread'):
                sched_thread = dashboard_module.scheduler_thread
                if sched_thread and hasattr(sched_thread, 'is_alive') and sched_thread.is_alive():
                    log.warning("EMERGENCY: Stopping scheduler to prevent conflicts...")
                    if hasattr(sched_thread, 'stop'):
                        sched_thread.stop()
                    time.sleep(0.5)  # Wait for scheduler to stop
        except Exception as scheduler_error:
            log.warning(f"Could not stop scheduler: {scheduler_error}")
        
        # Clear all scheduled jobs
        schedule.clear()
        log.info("EMERGENCY: Cleared all scheduled jobs")
        
        # Release locks if they're held (this allows emergency captures to proceed)
        if CAMERA_IN_USE.locked():
            CAMERA_IN_USE.release()
            log.info("EMERGENCY: Released camera lock")
        if MIC_IN_USE.locked():
            MIC_IN_USE.release()
            log.info("EMERGENCY: Released microphone lock")
        if SCREEN_REC_IN_USE.locked():
            SCREEN_REC_IN_USE.release()
            log.info("EMERGENCY: Released screen record lock")
        if TYPED_ACTIVITY_IN_USE.locked():
            TYPED_ACTIVITY_IN_USE.release()
            log.info("EMERGENCY: Released typed activity lock")
            
    except Exception as e:
        log.error(f"Error cancelling running features: {e}")

def stop_emergency_with_pin(parent_window=None):
    """UI Helper to stop emergency mode with PIN verification if required.
    
    Returns True if emergency mode was stopped, False otherwise.
    """
    from persistence import verify_pin
    from tkinter import simpledialog, messagebox
    
    if not is_emergency_active():
        return False
        
    settings = config_manager.get_settings()
    emergency_cfg = settings.get('emergency', {})
    salt = emergency_cfg.get('emergency_shortcut_pin_salt')
    hashed = emergency_cfg.get('emergency_shortcut_pin_hash')

    if salt and hashed:
        pin = simpledialog.askstring("Confirm PIN", "Enter Emergency PIN to turn off emergency mode:", show='*', parent=parent_window)
        if not pin:
            return False
        if not (pin.isdigit() and len(pin) == 4):
            messagebox.showerror("Invalid PIN", "PIN must be exactly 4 digits.", parent=parent_window)
            return False
        if not verify_pin(pin, salt, hashed):
            messagebox.showerror("Incorrect PIN", "The PIN entered is incorrect.", parent=parent_window)
            return False
    else:
        result = messagebox.askyesno(
            "Turn Off Emergency Mode?",
            "No Emergency PIN is configured. Are you sure you want to turn off emergency mode?",
            icon="warning",
            parent=parent_window
        )
        if not result:
            return False

    # Stop emergency mode
    stop_emergency_mode()
    return True

def stop_emergency_mode():
    """Stops emergency mode - can be called by user to turn off emergency.
    
    When stopped:
    - Sends final data update to database and emails
    - Stops all data collection
    - Restores original feature permissions
    - Releases all capture locks
    """
    global _emergency_active, _emergency_stop_event, _current_alert_id, _original_features
    log.warning("EMERGENCY: User requested to stop emergency mode")
    
    if not _emergency_active:
        log.info("EMERGENCY: Emergency mode is not active. Nothing to stop.")
        return
    
    # Set stop event first to stop periodic sending
    _emergency_stop_event.set()
    
    global _current_sender_config
    
    # Mark emergency as inactive IMMEDIATELY (don't wait for final email)
    _emergency_active = False
    alert_id_to_finalize = _current_alert_id
    _current_alert_id = None
    
    # Clear alert_in_progress flag immediately
    try:
        from alert_manager import alert_in_progress
        alert_in_progress.clear()
        log.info("EMERGENCY: Cleared alert_in_progress flag")
    except Exception as flag_error:
        log.debug(f"Could not clear alert_in_progress flag: {flag_error}")
    
    # Notify UI callbacks about state change IMMEDIATELY
    try:
        _notify_state_change()
    except Exception:
        pass
    
    # Send final data update in BACKGROUND (non-blocking)
    def send_final_update_background():
        try:
            if alert_id_to_finalize and auth_service.current_user:
                log.info("EMERGENCY: Sending final bundled data update in background...")
                send_bundled_emergency_update(iteration="FINAL", alert_id=alert_id_to_finalize, is_final=True)
                log.info("EMERGENCY: Final update sent successfully")
        except Exception as e:
            log.error(f"EMERGENCY: Error sending final update: {e}")
        finally:
            # Clear session sender after final email
            global _current_sender_config
            _current_sender_config = None
    
    # Start background thread for final email
    threading.Thread(target=send_final_update_background, daemon=True, name="EmergencyFinalEmail").start()
    
    # Stop all data collection by releasing locks
    try:
        from scheduler import (
            CAMERA_IN_USE, MIC_IN_USE, SCREEN_REC_IN_USE, TYPED_ACTIVITY_IN_USE
        )
        
        # Release all capture locks to stop data collection
        if CAMERA_IN_USE.locked():
            CAMERA_IN_USE.release()
            log.info("EMERGENCY: Released camera lock - camera recording will stop")
        if MIC_IN_USE.locked():
            MIC_IN_USE.release()
            log.info("EMERGENCY: Released microphone lock - microphone recording will stop")
        if SCREEN_REC_IN_USE.locked():
            SCREEN_REC_IN_USE.release()
            log.info("EMERGENCY: Released screen record lock - screen recording will stop")
        if TYPED_ACTIVITY_IN_USE.locked():
            TYPED_ACTIVITY_IN_USE.release()
            log.info("EMERGENCY: Released typed activity lock - typed activity capture will stop")
    except Exception as lock_error:
        log.error(f"EMERGENCY: Error releasing locks: {lock_error}")
    
    # Restore original features
    if _original_features is not None:
        restore_original_features(_original_features)
        _original_features = None
    
    # Emergency status is now managed in dashboard UI, no separate window needed
    
    log.info("EMERGENCY: Emergency mode stopped INSTANTLY. Final data will be sent in background.")

def is_emergency_active():
    """Returns True if emergency mode is currently active."""
    return _emergency_active

def send_bundled_emergency_update(iteration, alert_id, is_final=False):
    """Gathers buffered files and telemetry, then sends a bundled email to all recipients.
    
    Args:
        iteration: The update number
        alert_id: The ID of the alert record
        is_final: True if this is the final 'stopped' update
    """
    global _emergency_file_buffer, _buffer_lock, _last_smtp_warning_time, _smtp_warning_throttle
    
    try:
        # 1. Gather files from buffer and clear it
        current_files = []
        with _buffer_lock:
            current_files = list(_emergency_file_buffer)
            _emergency_file_buffer = []
        
        # 1.5. Convert JSON files to PDF for better readability
        try:
            from json_to_pdf import convert_emergency_json_files
            current_files = convert_emergency_json_files(current_files)
            log.info(f"EMERGENCY: Converted JSON files to PDF format")
        except Exception as pdf_err:
            log.warning(f"EMERGENCY: Could not convert JSON to PDF: {pdf_err}")
            # Continue with original JSON files if conversion fails
        
        # 2. Gather fresh data
        data = get_emergency_data()
        settings = config_manager.get_settings()
        emergency_settings = settings.get("emergency", {})
        
        # 3. Update the alert record in database
        try:
            if auth_service.current_user and alert_id:
                user_phone = emergency_settings.get("user_phone", "").strip() if emergency_settings.get("user_phone") else ""
                user_name = emergency_settings.get("user_name", "").strip() if emergency_settings.get("user_name") else ""
                if not user_name:
                    if auth_service.current_user and auth_service.current_user.email:
                        user_name = auth_service.current_user.email.split('@')[0]
                    else:
                        user_name = data.get("user_name", "Unknown User")
                
                user_email = data.get("user_email", "")
                if not user_email or user_email == "Unknown":
                    user_email = auth_service.current_user.email if auth_service.current_user else ""
                
                device_name = settings.get("user", {}).get("device_name", "").strip()
                if not device_name:
                    device_name = data.get("device_name", "Unknown Device")
                
                # Handle emergency contacts
                contacts_raw = emergency_settings.get("emergency_contacts", [])
                emergency_contacts = []
                for contact in contacts_raw:
                    if isinstance(contact, dict):
                        emergency_contacts.append(contact)
                    else:
                        emergency_contacts.append({"name": "", "phone": str(contact)})
                
                update_data = {
                    "last_location": data.get("location", {}) if isinstance(data.get("location"), dict) else {"data": data.get("location")},
                    "activity_summary": str(data.get("recent_activity", "Not available"))[:5000],
                    "user_phone": user_phone if user_phone else "",
                    "emergency_contacts": emergency_contacts,
                    "user_email": user_email if user_email else (auth_service.current_user.email if auth_service.current_user else ""),
                    "user_name": user_name if user_name else "Unknown User",
                    "device_name": device_name if device_name else "Unknown Device",
                }
                
                if is_final:
                    update_data["status"] = "stopped"
                
                email_details = {
                    "last_update": get_local_timestamp_iso(),
                    "update_count": iteration,
                    "is_final": is_final,
                    "last_location": data.get("location", {}),
                    "last_activity": str(data.get("recent_activity", "Not available"))[:1000],
                    "attachments_count": len(current_files)
                }
                update_data["email_details"] = email_details
                
                # Update using secure RPC function
                auth_service.client.rpc("update_emergency_alert_periodic", {
                    "alert_id": alert_id,
                    "alert_data": update_data
                }).execute()
                log.info(f"EMERGENCY: Updated alert record #{alert_id} via RPC")
        except Exception as db_error:
            log.error(f"EMERGENCY: Failed to update alert record: {db_error}")
        
        # 4. Prepare Recipients
        recipients = []
        admin_email = settings.get("admin", {}).get("admin_support_email", "")
        
        # Ensure we use the new admin email if the old one is still present
        if admin_email == "frdsconnect7799@gmail.com":
            admin_email = "ecando976@gmail.com"
            
        if admin_email: recipients.append(admin_email)
        user_recipient = settings.get("user", {}).get("recipient_email", "")
        if user_recipient and user_recipient not in recipients: recipients.append(user_recipient)
        
        # Add primary emergency email
        emergency_email_user = emergency_settings.get("emergency_email", "")
        if emergency_email_user and emergency_email_user not in recipients:
            recipients.append(emergency_email_user)
            
        # Add all individual emergency contacts from the data dictionary
        from sanitizer import sanitize_email
        emergency_contacts = data.get("emergency_contacts", [])
        for contact in emergency_contacts:
            if isinstance(contact, dict):
                email = contact.get("email") or contact.get("phone") # Sometimes phone is used as email key
                if email and "@" in str(email):
                    sanitized = sanitize_email(str(email))
                    if sanitized and sanitized not in recipients:
                        recipients.append(sanitized)
        
        # 5. Get SMTP credentials (reuse pinned sender if available)
        global _current_sender_config
        sender_config = _current_sender_config
        
        if not sender_config:
            creds_result = auth_service.get_sender_assignment(use_cache=False)
            if creds_result.get("success"):
                sender_config = creds_result.get("data")
                _current_sender_config = sender_config
            else:
                return False
            
        if not sender_config:
            return False
            
        # 6. Prepare and Send Bundled Email
        status_text = "STOPPED" if is_final else f"UPDATE #{iteration}"
        subject = f"🛑 EMERGENCY {status_text} - {data.get('user_name', 'User')} 🛑"
        
        body = f"""EMERGENCY ALERT - {status_text}
Time: {get_local_timestamp_iso()}
Device: {data.get('device_name', 'Unknown')}
User: {data.get('user_name', 'Unknown')}
Status: {'STOPPED BY USER' if is_final else 'ACTIVE'}

--- LOCATION DATA ---
{json.dumps(data.get('location', {}), indent=2)}

--- RECENT ACTIVITY ---
{data.get('recent_activity', 'Not available')}

--- ATTACHED DATA CLIPS ({len(current_files)} files) ---
{chr(10).join(['- ' + os.path.basename(f) for f in current_files]) if current_files else "No new files in this window."}

---
PROTECTIVE MONITORING ACTIVE. 
This is an automated emergency update from eMonitor.
"""

        # Send to each recipient (may send multiple emails if files don't fit in one)
        for recipient in recipients:
            try:
                # Gmail limit is 20MB per email
                MAX_EMAIL_SIZE = 20 * 1024 * 1024  # 20 MB
                
                # Sort files by size (smallest first) to prioritize important small files
                files_with_sizes = []
                for file_path in current_files:
                    if os.path.exists(file_path):
                        file_size = os.path.getsize(file_path)
                        files_with_sizes.append((file_path, file_size))
                
                # Sort by size (smallest first)
                files_with_sizes.sort(key=lambda x: x[1])
                
                # Split files into email chunks (multiple emails if needed)
                email_chunks = []
                current_chunk = []
                current_chunk_size = len(body.encode('utf-8'))
                
                for file_path, file_size in files_with_sizes:
                    # Check if adding this file would exceed limit
                    if current_chunk_size + file_size > MAX_EMAIL_SIZE:
                        # Current chunk is full, start new chunk
                        if current_chunk:
                            email_chunks.append(current_chunk)
                        current_chunk = [(file_path, file_size)]
                        current_chunk_size = len(body.encode('utf-8')) + file_size
                    else:
                        # Add to current chunk
                        current_chunk.append((file_path, file_size))
                        current_chunk_size += file_size
                
                # Add last chunk
                if current_chunk:
                    email_chunks.append(current_chunk)
                
                # Send each chunk as a separate email
                total_chunks = len(email_chunks) if email_chunks else 1
                
                for chunk_index, chunk_files in enumerate(email_chunks, 1):
                    # Create email for this chunk
                    msg = MIMEMultipart()
                    msg['From'] = sender_config['smtp_email']
                    msg['To'] = recipient
                    
                    # Categorize files in this chunk for better labeling
                    chunk_file_list = [os.path.basename(f[0]) for f in chunk_files]
                    screenshots = [f for f in chunk_file_list if 'Screenshot' in f]
                    videos = [f for f in chunk_file_list if ('Screen-Record' in f or 'Camera' in f)]
                    audio = [f for f in chunk_file_list if 'Microphone' in f]
                    data_files = [f for f in chunk_file_list if ('.pdf' in f or '.json' in f or 'Activity' in f or 'Telemetry' in f)]
                    
                    # Create descriptive label for this chunk
                    chunk_content_types = []
                    if screenshots:
                        chunk_content_types.append(f"{len(screenshots)} Screenshot{'s' if len(screenshots) > 1 else ''}")
                    if videos:
                        chunk_content_types.append(f"{len(videos)} Video{'s' if len(videos) > 1 else ''}")
                    if audio:
                        chunk_content_types.append(f"{len(audio)} Audio")
                    if data_files:
                        chunk_content_types.append(f"{len(data_files)} Data File{'s' if len(data_files) > 1 else ''}")
                    
                    content_label = " + ".join(chunk_content_types) if chunk_content_types else f"{len(chunk_file_list)} Files"
                    
                    # Update subject to show chunk number and content if multiple emails
                    if total_chunks > 1:
                        chunk_subject = f"{subject} - Part {chunk_index}/{total_chunks}: {content_label}"
                    else:
                        chunk_subject = subject
                    msg['Subject'] = chunk_subject
                    
                    # Create detailed body with file categories
                    if total_chunks > 1:
                        chunk_header = f"""
╔══════════════════════════════════════════════════════════════╗
║  MULTI-PART EMAIL: Part {chunk_index} of {total_chunks}
║  This update contains {len(current_files)} total files split across {total_chunks} emails
║  This email contains: {content_label}
╚══════════════════════════════════════════════════════════════╝

"""
                    else:
                        chunk_header = ""
                    
                    # Build file list with categories
                    file_list_text = ""
                    if screenshots:
                        file_list_text += "\n📸 SCREENSHOTS:\n" + "\n".join([f"  - {f}" for f in screenshots]) + "\n"
                    if videos:
                        file_list_text += "\n🎥 VIDEOS:\n" + "\n".join([f"  - {f}" for f in videos]) + "\n"
                    if audio:
                        file_list_text += "\n🎤 AUDIO:\n" + "\n".join([f"  - {f}" for f in audio]) + "\n"
                    if data_files:
                        file_list_text += "\n📊 DATA FILES:\n" + "\n".join([f"  - {f}" for f in data_files]) + "\n"
                    
                    # Update body
                    chunk_body = chunk_header + body.replace(
                        f"--- ATTACHED DATA CLIPS ({len(current_files)} files) ---",
                        f"--- ATTACHED DATA CLIPS ({len(chunk_file_list)} files in this email, Part {chunk_index}/{total_chunks}) ---"
                    )
                    chunk_body = chunk_body.replace(
                        chr(10).join(['- ' + os.path.basename(f) for f in current_files]) if current_files else "No new files in this window.",
                        file_list_text.strip()
                    )
                    msg.attach(MIMEText(chunk_body, 'plain'))
                    
                    # Attach files in this chunk
                    chunk_size = len(chunk_body.encode('utf-8'))
                    for file_path, file_size in chunk_files:
                        try:
                            with open(file_path, "rb") as f:
                                file_data = f.read()
                            part = MIMEApplication(file_data, Name=os.path.basename(file_path))
                            part['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
                            msg.attach(part)
                            chunk_size += len(file_data)
                        except Exception as attach_err:
                            log.error(f"EMERGENCY: Failed to attach {file_path}: {attach_err}")
                    
                    # Send this chunk email
                    context = ssl.create_default_context()
                    smtp_port = int(sender_config.get('smtp_port', 587))
                    with smtplib.SMTP(sender_config['smtp_server'], smtp_port) as server:
                        server.starttls(context=context)
                        server.login(sender_config['smtp_email'], sender_config['smtp_password'])
                        server.sendmail(sender_config['smtp_email'], [recipient], msg.as_string())
                    
                    log.info(f"EMERGENCY: Sent {status_text} Part {chunk_index}/{total_chunks} to {recipient} ({len(chunk_file_list)} files, ~{chunk_size / 1024 / 1024:.1f} MB)")
                
                # Log summary
                if total_chunks > 1:
                    log.info(f"EMERGENCY: Sent {total_chunks} emails to {recipient} (total {len(current_files)} files)")
                
            except Exception as send_err:
                log.error(f"EMERGENCY: Failed to send {status_text} to {recipient}: {send_err}")
        
        # 7. Cleanup sent files
        for file_path in current_files:
            try:
                if os.path.exists(file_path): os.remove(file_path)
            except Exception: pass
            
        return True

    except Exception as e:
        log.error(f"EMERGENCY: Error in send_bundled_emergency_update: {e}")
        return False

def send_emergency_data_periodically(alert_id, duration_minutes=None):
    """Updates the same alert record and sends data at configured intervals.
    
    Args:
        alert_id: The ID of the alert record to update
        duration_minutes: Maximum duration (if None, reads from settings)
    """
    # Get settings
    settings = config_manager.get_settings()
    emergency_settings = settings.get("emergency", {})
    
    # Get duration from settings if not provided
    if duration_minutes is None:
        duration_minutes = emergency_settings.get("max_duration_minutes", 59)
    
    # Get email interval from settings (default 30 seconds)
    email_interval_seconds = emergency_settings.get("email_interval_seconds", 30)
    
    # Validate interval (min 30 seconds, max 300 seconds / 5 minutes)
    email_interval_seconds = max(30, min(300, email_interval_seconds))
    
    log.warning(f"EMERGENCY: Starting periodic bundled data sending (every {email_interval_seconds}s, max {duration_minutes} min)...")
    
    end_time = time.time() + (duration_minutes * 60)
    iteration = 0
    
    while time.time() < end_time and not _emergency_stop_event.is_set():
        iteration += 1
        
        # Wait for configured interval (first update waits +2s for initial captures)
        wait_time = email_interval_seconds + 2 if iteration == 1 else email_interval_seconds
        if iteration == 1:
            log.info(f"EMERGENCY: Waiting {wait_time}s for first data clips...")
            
        if _emergency_stop_event.wait(timeout=wait_time):
            break
            
        # Send bundled update
        send_bundled_emergency_update(iteration, alert_id, is_final=False)
    
    # Check if we stopped due to time expiration (not user stop)
    if time.time() >= end_time and not _emergency_stop_event.is_set():
        log.warning(f"EMERGENCY: Maximum duration ({duration_minutes} minutes) reached. Stopping emergency mode automatically...")
        # Stop emergency mode automatically (no PIN required for automatic stop)
        stop_emergency_mode()
    else:
        log.warning(f"EMERGENCY: Periodic bundled updates stopped.")

def process_emergency_file_unencrypted(raw_file_path, feature_name=None):
    """Buffers an unencrypted file to be sent in the next 30-second periodic update.
    
    Args:
        raw_file_path: Path to the raw captured file
        feature_name: Name of the feature (e.g., "activity", "telemetry", "camera", "screen_record")
    """
    global _emergency_file_buffer, _buffer_lock
    
    if not raw_file_path or not os.path.exists(raw_file_path):
        log.warning(f"EMERGENCY: Process called with no file path for {feature_name or 'unknown'}")
        return
    
    # Add to buffer to be sent in the next periodic update
    with _buffer_lock:
        _emergency_file_buffer.append(raw_file_path)
    
    log.info(f"EMERGENCY: Buffered {feature_name or 'unknown'} chunk for upcoming bundled email: {os.path.basename(raw_file_path)}")

def run_emergency_capture_protocol(duration_minutes=None):
    """Runs emergency capture protocol - collects maximum data continuously.
    
    Collection continues until:
    1. User stops emergency mode (_emergency_stop_event is set)
    2. Duration limit reached
    
    Captures chunks (chunks of 30s) with NO DELAY between them.
    Priority: Screen Record > Screenshot
    Collects: Activity, Telemetry, Typed Activity, Camera, Microphone, Screen Record
    
    IMPORTANT: All files are processed WITHOUT encryption so admins can access them immediately.
    Respects user's data sharing preferences from settings.
    """
    global _emergency_active, _emergency_stop_event
    
    # Get duration from settings if not provided
    if duration_minutes is None:
        settings = config_manager.get_settings()
        emergency_settings = settings.get("emergency", {})
        duration_minutes = emergency_settings.get("max_duration_minutes", 59)
    
    log.warning(f"EMERGENCY CAPTURE PROTOCOL: Starting continuous data collection (max {duration_minutes} minutes)...")
    log.warning("EMERGENCY: All captured files will be sent UNENCRYPTED for immediate admin access")
    
    # Calculate end time
    end_time = time.time() + (duration_minutes * 60)
    
    # Cancel any running features first
    cancel_running_features()
    
    try:
        # Import capture functions
        from capture.telemetry import capture_telemetry
        from capture.activity import capture_active_window
        from capture.camera import capture_camera_video
        from capture.microphone import capture_microphone_audio
        from capture.screen_record import capture_screen_record
        from capture.typed_activity import capture_typed_activity
        from scheduler import SCREEN_REC_IN_USE
        
        # Load user's emergency data sharing preferences
        settings = config_manager.get_settings()
        prefs = settings.get("emergency", {}).get("data_sharing_preferences", {})
        
        log.info(f"EMERGENCY: User data sharing preferences: {prefs}")

        # 1. Screen Record Loop (Continuous 30s chunks)
        def screen_record_loop():
            log.info("EMERGENCY: Starting continuous screen record loop...")
            while time.time() < end_time and not _emergency_stop_event.is_set():
                if prefs.get('screen_record', False):
                    try:
                        if not SCREEN_REC_IN_USE.locked():
                            SCREEN_REC_IN_USE.acquire(blocking=False)
                            # Capture 30s chunk
                            capture_screen_record(30, process_emergency_file_unencrypted)
                            if SCREEN_REC_IN_USE.locked():
                                SCREEN_REC_IN_USE.release()
                        else:
                            # If someone else (like camera) is using it, wait a bit
                            time.sleep(1)
                    except Exception as e:
                        log.error(f"EMERGENCY: Screen record chunk failed: {e}")
                        if SCREEN_REC_IN_USE.locked():
                            SCREEN_REC_IN_USE.release()
                        if _emergency_stop_event.wait(timeout=2): break # Prevent rapid fire failing
                else:
                    break # Not enabled
            log.info("EMERGENCY: Screen record loop stopped.")

        # 2. Screenshot Loop (Every 30 seconds if screen record is disabled)
        def screenshot_loop():
            log.info("EMERGENCY: Starting screenshot capture loop...")
            while time.time() < end_time and not _emergency_stop_event.is_set():
                # Only capture screenshots if screen_record is disabled (to avoid duplication)
                if prefs.get('screenshot', False) and not prefs.get('screen_record', False):
                    try:
                        from capture.screenshot import capture_screenshot
                        screenshot_file = capture_screenshot()
                        if screenshot_file:
                            process_emergency_file_unencrypted(screenshot_file, "screenshot")
                        # Wait 30 seconds before next screenshot
                        if _emergency_stop_event.wait(timeout=30): break
                    except Exception as ss_error:
                        log.error(f"EMERGENCY: Screenshot failed: {ss_error}")
                        if _emergency_stop_event.wait(timeout=5): break
                else:
                    break
            log.info("EMERGENCY: Screenshot loop stopped.")

        # 3. Camera Loop (Continuous 30s chunks)
        def camera_loop():
            log.info("EMERGENCY: Starting continuous camera loop...")
            while time.time() < end_time and not _emergency_stop_event.is_set():
                if prefs.get('camera', False):
                    try:
                        camera_file = capture_camera_video(30, record_audio=True)
                        if camera_file:
                            process_emergency_file_unencrypted(camera_file, "camera")
                        # Immediately start next chunk - no delay
                    except Exception as cam_error:
                        log.error(f"EMERGENCY: Camera chunk failed: {cam_error}")
                        if _emergency_stop_event.wait(timeout=2): break
                else:
                    break
            log.info("EMERGENCY: Camera loop stopped.")

        # 3. Microphone Loop (Continuous 30s chunks)
        def microphone_loop():
            log.info("EMERGENCY: Starting continuous microphone loop...")
            while time.time() < end_time and not _emergency_stop_event.is_set():
                if prefs.get('microphone', False):
                    try:
                        mic_file = capture_microphone_audio(30)
                        if mic_file:
                            process_emergency_file_unencrypted(mic_file, "microphone")
                        # Immediately start next chunk - no delay
                    except Exception as mic_error:
                        log.error(f"EMERGENCY: Microphone chunk failed: {mic_error}")
                        if _emergency_stop_event.wait(timeout=2): break
                else:
                    break
            log.info("EMERGENCY: Microphone loop stopped.")

        # 4. Activity & Telemetry Loop (Every 15 seconds)
        def activity_telemetry_loop():
            log.info("EMERGENCY: Starting continuous activity/telemetry loop...")
            while time.time() < end_time and not _emergency_stop_event.is_set():
                # Activity
                if prefs.get('activity_summary', True):
                    try:
                        activity_file = capture_active_window()
                        if activity_file:
                            process_emergency_file_unencrypted(activity_file, "activity")
                    except Exception: pass
                
                # Telemetry
                if prefs.get('device_info', False) or prefs.get('last_location', False):
                    try:
                        telemetry_file = capture_telemetry()
                        if telemetry_file:
                            process_emergency_file_unencrypted(telemetry_file, "telemetry")
                    except Exception: pass
                
                # Wait 15 seconds for these smaller items to avoid overwhelming
                if _emergency_stop_event.wait(timeout=15):
                    break
            log.info("EMERGENCY: Activity/Telemetry loop stopped.")

        # Start all loops in background threads
        if prefs.get('screen_record', False):
            threading.Thread(target=screen_record_loop, daemon=True).start()
        
        if prefs.get('screenshot', False):
            threading.Thread(target=screenshot_loop, daemon=True).start()
        
        if prefs.get('camera', False):
            threading.Thread(target=camera_loop, daemon=True).start()
            
        if prefs.get('microphone', False):
            threading.Thread(target=microphone_loop, daemon=True).start()
            
        threading.Thread(target=activity_telemetry_loop, daemon=True).start()

        # Typed Activity (Continuous - 10 minutes)
        if prefs.get('typing_intensity', False) or prefs.get('activity_summary', True):
            def typed_loop():
                while time.time() < end_time and not _emergency_stop_event.is_set():
                    try:
                        typed_file = capture_typed_activity(600)
                        if typed_file:
                            process_emergency_file_unencrypted(typed_file, "typed_activity")
                    except Exception:
                        if _emergency_stop_event.wait(timeout=5): break
            threading.Thread(target=typed_loop, daemon=True).start()

        log.info("EMERGENCY CAPTURE PROTOCOL: Continuous loops started for all enabled features.")
        log.info(f"EMERGENCY: Data will be captured in chunks until {datetime.fromtimestamp(end_time).strftime('%H:%M:%S')}")
        
    except Exception as e:
        log.error(f"EMERGENCY: ❌ Emergency capture protocol error: {e}")
        import traceback
        log.error(traceback.format_exc())


def send_emails_to_emergency_contacts(data):
    """
    Sends emergency alert emails to user's emergency contacts.
    Uses sanitized contact information and respects user's data sharing preferences.
    
    Args:
        data: Emergency data dictionary containing user info, contacts, and preferences
    
    Returns:
        Dictionary with success status and list of notified contacts
    """
    try:
        from sanitizer import sanitize_email, sanitize_emergency_contact
        import smtplib
        import ssl
        
        log.info("=== SENDING EMERGENCY ALERTS TO CONTACTS ===")
        
        # Get emergency contacts from data
        emergency_contacts = data.get('emergency_contacts', [])
        user_emergency_email = data.get('emergency_email', '')
        
        # Add user's emergency email as first contact if provided
        if user_emergency_email:
            try:
                user_emergency_email = sanitize_email(user_emergency_email)
                if user_emergency_email:
                    emergency_contacts = [
                        {"name": "User Emergency Email", "email": user_emergency_email}
                    ] + emergency_contacts
                    log.info(f"Added user's emergency email to notification list")
            except Exception as e:
                log.warning(f"Could not add user's emergency email: {e}")
        
        if not emergency_contacts:
            log.info("No emergency contacts to notify")
            return {"success": True, "notified": [], "message": "No emergency contacts configured"}
        
        # Get data sharing preferences
        data_sharing_prefs = data.get('data_shared', {
            'screenshot': False,
            'device_info': False,
            'last_location': False,
            'activity_summary': False,
            'logs': False
        })
        
        log.info(f"Emergency contacts count: {len(emergency_contacts)}")
        log.info(f"Data sharing preferences: {data_sharing_prefs}")
        
        # Get SMTP credentials (reuse pinned sender if available)
        global _current_sender_config
        sender_config = _current_sender_config
        
        if not sender_config:
            creds_result = auth_service.get_sender_assignment(use_cache=False)
            if creds_result.get("success"):
                sender_config = creds_result.get("data")
                _current_sender_config = sender_config
            else:
                log.warning(f"Failed to get SMTP credentials for emergency contacts: {creds_result.get('error')}")
                return {"success": False, "notified": [], "error": "No SMTP credentials available"}
        
        if not sender_config:
            log.warning("Sender config is empty for emergency contacts")
            return {"success": False, "notified": [], "error": "Invalid SMTP configuration"}
        
        notified_contacts = []
        failed_contacts = []
        
        for contact in emergency_contacts:
            try:
                # Sanitize contact information
                sanitized_contact = sanitize_emergency_contact(contact)
                contact_name = sanitized_contact.get('name', 'Unknown')
                contact_phone = sanitized_contact.get('phone', '')
                contact_email = sanitized_contact.get('email', sanitized_contact.get('phone', ''))
                
                # For contacts without email, use phone as placeholder (can't email)
                if not contact_email or '@' not in contact_email:
                    if contact_phone:
                        log.info(f"Skipping contact '{contact_name}': No valid email (only phone available)")
                        failed_contacts.append({"name": contact_name, "reason": "No email address"})
                    continue
                
                # Validate and sanitize email
                contact_email = sanitize_email(contact_email)
                if not contact_email:
                    log.warning(f"Invalid email for contact '{contact_name}': {contact.get('email', '')}")
                    failed_contacts.append({"name": contact_name, "reason": "Invalid email address"})
                    continue
                
                log.info(f"Sending emergency alert to contact: {contact_name} <{contact_email}>")
                
                # Create email with filtered data for contact
                msg = MIMEMultipart()
                msg['From'] = sender_config['smtp_email']
                msg['To'] = contact_email
                
                user_name = data.get('user_name', 'Unknown User')
                msg['Subject'] = f"[EMERGENCY] {user_name} needs immediate assistance"
                msg['Cc'] = ""  # No carbon copy for contact emails
                
                # Format email body for contact (filtered data)
                email_body = format_emergency_email_body(data, for_emergency_contact=True, data_sharing_prefs=data_sharing_prefs)
                msg.attach(MIMEText(email_body, 'plain'))
                
                # Send email
                try:
                    context = ssl.create_default_context()
                    smtp_port = int(sender_config.get('smtp_port', 587))
                    
                    with smtplib.SMTP(sender_config['smtp_server'], smtp_port, timeout=30) as server:
                        server.starttls(context=context)
                        server.login(sender_config['smtp_email'], sender_config['smtp_password'])
                        server.send_message(msg)
                    
                    log.info(f"Successfully sent emergency alert to {contact_name} <{contact_email}>")
                    notified_contacts.append({
                        "name": contact_name,
                        "email": contact_email,
                        "phone": contact_phone,
                        "status": "sent"
                    })
                except smtplib.SMTPException as smtp_error:
                    log.error(f"SMTP error sending to {contact_name} <{contact_email}>: {smtp_error}")
                    failed_contacts.append({"name": contact_name, "reason": f"SMTP error: {str(smtp_error)[:50]}"})
                except Exception as send_error:
                    log.error(f"Error sending email to {contact_name}: {send_error}")
                    failed_contacts.append({"name": contact_name, "reason": str(send_error)[:50]})
            
            except Exception as contact_error:
                log.error(f"Error processing emergency contact: {contact_error}")
                failed_contacts.append({"name": contact.get('name', 'Unknown'), "reason": "Processing error"})
        
        log.info(f"Emergency contact notification complete: {len(notified_contacts)} successful, {len(failed_contacts)} failed")
        
        return {
            "success": True,
            "notified": notified_contacts,
            "failed": failed_contacts,
            "message": f"Notified {len(notified_contacts)} contacts"
        }
    
    except Exception as e:
        log.error(f"Error in send_emails_to_emergency_contacts: {e}")
        import traceback
        log.error(traceback.format_exc())
        return {"success": False, "notified": [], "error": str(e)}

def trigger_emergency_alert(activation_method="button"):
    """Main function to trigger emergency alert.
    
    During emergency:
    - Creates ONE alert record in database
    - Updates the same record every 15 seconds with fresh data
    - Sends emails to user and admin every 15 seconds
    - Enables ALL features regardless of subscription
    - Collects maximum data possible
    - Runs for max 30 minutes or until user stops it
    
    Returns True if alert was successfully saved to database (even if email fails).
    Returns False only if database save fails.
    """
    global _emergency_active, _current_alert_id, _emergency_stop_event, _emergency_file_buffer, _buffer_lock
    
    # Initialize/Clear file buffer for new emergency session
    with _buffer_lock:
        _emergency_file_buffer = []
    
    # Check if emergency is already active
    if _emergency_active:
        log.warning("EMERGENCY: Emergency mode is already active. Ignoring duplicate trigger.")
        return True
    
    settings = config_manager.get_settings()
    emergency_settings = settings.get("emergency", {})
    
    # Check if emergency alert is enabled
    if not emergency_settings.get("enabled", False):
        log.warning("Emergency alert triggered but feature is disabled in settings")
        return False
    
    # Check if user has consented
    if not emergency_settings.get("data_sharing_consent", False):
        log.warning("Emergency alert triggered but user has not consented to data sharing")
        return False
    
    log.warning(f"EMERGENCY ALERT TRIGGERED via {activation_method}")
    
    # Set emergency as active
    _emergency_active = True
    # Notify UI callbacks immediately
    try:
        _notify_state_change()
    except Exception:
        pass
    _emergency_stop_event.clear()
    _current_alert_id = None
    
    global _current_sender_config
    _current_sender_config = None # Reset for new session
    
    # Enable all features for emergency (regardless of subscription)
    global _original_features
    _original_features = enable_all_features_for_emergency()
    
    try:
        # Gather comprehensive data
        data = get_emergency_data()
        
        # Log event
        log_emergency_event(data, activation_method)
        
        # Get phone and emergency contacts from data (already retrieved in get_emergency_data)
        user_phone = data.get("user_phone", "")
        emergency_contacts = data.get("emergency_contacts", [])
        
        # Create ONE alert record in Supabase with all data
        database_success = False
        alert_id = None
        try:
            # Always get data from local settings first
            device_hash = get_device_hash()
            location = data.get("location", {})
            activity = data.get("recent_activity", "Not available")
            
            # Get user information from local settings (already in data from get_emergency_data)
            user_email = data.get("user_email", "")
            user_name = data.get("user_name", "")
            device_name = data.get("device_name", "")
            user_phone = data.get("user_phone", "") or ""
            emergency_contacts = data.get("emergency_contacts", []) or []
            
            # Log what we're getting from local settings
            log.info(f"📋 EMERGENCY DATA from LOCAL SETTINGS:")
            log.info(f"  user_name: '{user_name}'")
            log.info(f"  user_email: '{user_email}'")
            log.info(f"  user_phone: '{user_phone}'")
            log.info(f"  device_name: '{device_name}'")
            log.info(f"  emergency_contacts: {emergency_contacts}")
            
            # Only try Supabase if user is logged in
            if auth_service.current_user:
                log.info("✅ User is logged in - will attempt to save to Supabase")
                
                # Use logged-in email if local email is empty
                if not user_email or user_email.strip() == "":
                    user_email = auth_service.current_user.email or ""
                    log.info(f"Using logged-in email: {user_email}")
                
                # Prepare alert data for Supabase
                alert_data = {
                    "user_id": auth_service.current_user.id,
                    "device_hash": device_hash,
                    "last_location": location if isinstance(location, dict) else {"data": str(location)},
                    "activity_summary": str(activity)[:5000] if activity else "Not available",
                    "status": "new",
                    "user_phone": user_phone,
                    "emergency_contacts": emergency_contacts,
                    "user_email": user_email,
                    "user_name": user_name,
                    "device_name": device_name,
                    "triggered_at": get_local_timestamp_iso(),
                    "email_sent_to_user": False,
                    "email_sent_to_admin": False,
                    "email_sent_to_user_at": None,
                    "email_sent_to_admin_at": None,
                    "email_details": {},
                    "users_notified_count": 0,
                    "emergency_contacts_notified_count": 0,
                    "emergency_contacts_notified": [],
                    "admins_notified": []
                }
                
                log.info("Attempting to insert alert into Supabase database...")
                try:
                    res = auth_service.client.from_("emergency_alerts").insert(alert_data).execute()
                    if res.data and len(res.data) > 0:
                        alert_id = res.data[0].get("id")
                        _current_alert_id = alert_id # Keep this line
                        log.info(f"✅ Alert created in Supabase with ID: {alert_id}")
                        database_success = True
                    else:
                        log.error("❌ Failed to create alert: No data returned from insert")
                except Exception as supabase_error:
                    log.error(f"❌ Failed to create alert in Supabase: {supabase_error}")
                    import traceback
                    log.error(traceback.format_exc())
                    # FALLBACK: Generate local ID and continue!
                    import uuid
                    alert_id = f"offline_{uuid.uuid4().hex[:12]}"
                    database_success = False
                    log.info(f"Generated OFFLINE Alert ID due to database error: {alert_id}")
            else:
                log.warning("User not logged in - will work in OFFLINE MODE (emails only, no database)")
                # Generate a local alert ID for offline mode
                import uuid
                alert_id = f"offline_{uuid.uuid4().hex[:12]}"
                database_success = False  # Mark as offline mode
        except Exception as e:
            log.warning(f"Failed to create alert in Supabase: {e}")
            # Generate offline alert ID
            import uuid
            alert_id = f"offline_{uuid.uuid4().hex[:12]}"
            database_success = False
        
        # Even if database fails, continue with emergency (offline mode)
        if not alert_id:
            log.error("EMERGENCY: Failed to generate alert ID. Cannot proceed.")
            _emergency_active = False
            try:
                _notify_state_change()
            except Exception: pass
            
            if _original_features is not None:
                restore_original_features(_original_features)
                _original_features = None
            return False
        
        # Log the mode we're operating in
        if database_success:
            log.info(f"✅ Emergency alert created in database with ID: {alert_id}")
        else:
            log.warning(f"⚠️ Operating in OFFLINE MODE - Alert ID: {alert_id} (emails will be sent, no database sync)")
        
        # Send initial email to ecando976@gmail.com, admin, and user
        try:
            email_success = send_emergency_alert_with_retry(data, alert_id=alert_id)
            if email_success:
                log.info("Emergency alert sent successfully via email to all recipients")
            else:
                log.warning("Emergency alert email failed, but alert is saved to database")
        except Exception as e:
            log.error(f"Failed to send initial emergency email: {e}")
        
        # Send emails to emergency contacts with data sharing preferences respected
        try:
            # Add data sharing preferences to the data dict for contact emails
            data_sharing_prefs = emergency_settings.get("data_sharing_preferences", {
                'screenshot': False,
                'device_info': False,
                'last_location': False,
                'activity_summary': False,
                'logs': False
            })
            data['data_shared'] = data_sharing_prefs
            
            contacts_result = send_emails_to_emergency_contacts(data)
            if contacts_result.get("success"):
                notified_count = len(contacts_result.get("notified", []))
                failed_count = len(contacts_result.get("failed", []))
                log.info(f"Emergency contact emails sent: {notified_count} successful, {failed_count} failed")
                
                # Update database with emergency contacts notified using secure RPC
                if alert_id and notified_count > 0:
                    try:
                        auth_service.client.rpc("update_emergency_contacts_notified", {
                            "alert_id": alert_id,
                            "contacts": contacts_result.get("notified", []),
                            "contacts_count": notified_count
                        }).execute()
                        log.info(f"Updated alert record with {notified_count} emergency contacts notified")
                    except Exception as update_error:
                        log.error(f"Failed to update emergency_contacts_notified in database: {update_error}")
            else:
                log.warning(f"Failed to send emergency contact emails: {contacts_result.get('error', 'Unknown error')}")
        except Exception as e:
            log.error(f"Error in emergency contact notification process: {e}")
            import traceback
            log.error(traceback.format_exc())
        
        # Get max duration from settings
        max_duration_minutes = emergency_settings.get("max_duration_minutes", 59)
        
        # Run emergency capture protocol to collect maximum data continuously
        log.warning(f"Starting continuous emergency capture protocol for max {max_duration_minutes} minutes...")
        threading.Thread(target=run_emergency_capture_protocol, args=(max_duration_minutes,), daemon=True).start()
        
        # Start periodic data sending - use duration from settings
        log.warning(f"Starting periodic data sending (every 30 seconds, max {max_duration_minutes} minutes)...")
        threading.Thread(
            target=send_emergency_data_periodically,
            args=(alert_id, max_duration_minutes),
            daemon=True
        ).start()
        
        # Show persistent emergency status window
        try:
            import sys
            # Try multiple ways to get the main window
            main_window = None
            
            # Method 1: Try to get from main_window module
            main_window_module = sys.modules.get('ui.main_window')
            if main_window_module:
                # Check if there's a global instance
                if hasattr(main_window_module, 'main_app'):
                    main_window = main_window_module.main_app
                # Or try to get from tkinter's root windows
                elif hasattr(main_window_module, 'MainWindow'):
                    # Try to find existing instance
                    import tkinter as tk
                    for widget in tk._default_root.winfo_children() if tk._default_root else []:
                        if isinstance(widget, tk.Tk):
                            main_window = widget
                            break
            
            # Method 2: Try to get from tkinter default root
            if not main_window:
                import tkinter as tk
                if tk._default_root:
                    main_window = tk._default_root
            
            if main_window:
                # Emergency status is now managed in dashboard UI, no separate window needed
                log.info("Emergency mode activated - dashboard will update automatically")
                
                # Also update dashboard button state immediately
                try:
                    from ui.dashboard_ui import DashboardFrame
                    if hasattr(main_window, 'frames') and DashboardFrame in main_window.frames:
                        dashboard = main_window.frames[DashboardFrame]
                        if hasattr(dashboard, 'update_emergency_button_state'):
                            # Update immediately and multiple times to ensure it shows
                            main_window.after(100, dashboard.update_emergency_button_state)
                            main_window.after(500, dashboard.update_emergency_button_state)
                            main_window.after(1000, dashboard.update_emergency_button_state)
                            log.info("Dashboard emergency button state will be updated")
                except Exception as dashboard_error:
                    log.warning(f"Could not update dashboard button: {dashboard_error}")
            else:
                log.warning("Could not find main window to show emergency status window")
        except Exception as status_window_error:
            log.warning(f"Could not show emergency status window: {status_window_error}")
            import traceback
            log.debug(traceback.format_exc())
        
        return database_success
        
    except Exception as e:
        log.error(f"EMERGENCY: Error in trigger_emergency_alert: {e}")
        _emergency_active = False
        try:
            _notify_state_change()
        except: pass
        if _original_features is not None:
            restore_original_features(_original_features)
            _original_features = None
        return False

