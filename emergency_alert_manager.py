import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
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
from capture.activity import get_active_window_data

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
        
        if data_sharing_prefs.get('screenshot', False):
            body_parts.append(f"\nScreenshot has been taken and is attached.\n")
        
        if data_sharing_prefs.get('logs', False):
            body_parts.append(f"\nApplication logs have been included in a separate attachment.\n")
        
        if data_sharing_prefs.get('camera', False):
            body_parts.append(f"\nCamera capture has been taken and is attached.\n")
        
        if data_sharing_prefs.get('microphone', False):
            body_parts.append(f"\nMicrophone audio has been recorded and is attached.\n")
        
        if data_sharing_prefs.get('screen_record', False):
            body_parts.append(f"\nA short screen recording has been captured and is attached.\n")
        
        body_parts.append("\n--- Emergency Contact Notification ---\n")
        body_parts.append("This is an automated emergency notification. Please contact the user or emergency services if needed.\n")
        
        body = "".join(body_parts)
    else:
        # Full body for admin (always gets all data)
        body = f"""
EMERGENCY ALERT - IMMEDIATE ACTION REQUIRED

User Information:
- Name: {data.get('user_name', 'Unknown')}
- Email: {data.get('user_email', 'Unknown')}
- Phone: {data.get('user_phone', 'Not provided')}
- Device ID: {data.get('device_id', 'Unknown')}
- Device Name: {data.get('device_name', 'Unknown')}
- Timestamp: {data.get('timestamp', 'Unknown')}

Location Information:
{json.dumps(data.get('location', 'Not available'), indent=2)}

Recent Activity:
{data.get('recent_activity', 'Not available')}

Emergency Contacts Registered:
"""
        emergency_contacts = data.get('emergency_contacts', [])
        if emergency_contacts and isinstance(emergency_contacts, list):
            for contact in emergency_contacts:
                if isinstance(contact, dict):
                    contact_name = contact.get('name', 'Unknown')
                    contact_phone = contact.get('phone', 'No phone')
                    contact_email = contact.get('email', '')
                    if contact_email:
                        body += f"\n- {contact_name}: {contact_phone} ({contact_email})"
                    else:
                        body += f"\n- {contact_name}: {contact_phone}"
                elif isinstance(contact, str):
                    body += f"\n- {contact}"
        else:
            body += "\nNone provided"
        
        body += "\n\nData Shared With Contacts:"
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
        
        # Get admin email and user email from settings (prefer explicit emergency settings)
        settings = config_manager.get_settings()
        emergency_settings = settings.get("emergency", {})
        admin_email = settings.get("admin", {}).get("admin_support_email", "")
        # Prefer emergency-specific recipient if provided, otherwise fallback to user.recipient_email
        user_email = emergency_settings.get("user_recipient_email") or settings.get("user", {}).get("recipient_email", "")
        # Also allow an explicit emergency_email field (user-provided emergency recipient)
        emergency_email_user = emergency_settings.get("emergency_email", "")
        
        # Always send to emergency email (ecando976@gmail.com)
        # Also include admin email, user email, and emergency email if configured
        recipients = [EMERGENCY_EMAIL]
        if admin_email and admin_email not in recipients and admin_email != EMERGENCY_EMAIL:
            recipients.append(admin_email)
        if user_email and user_email not in recipients and user_email != EMERGENCY_EMAIL:
            recipients.append(user_email)
        if emergency_email_user and emergency_email_user not in recipients and emergency_email_user != EMERGENCY_EMAIL:
            recipients.append(emergency_email_user)
        
        # Create email
        msg = MIMEMultipart()
        msg['From'] = sender_config['smtp_email']
        msg['To'] = ", ".join(recipients)
        user_name = data.get('user_name', data.get('user_email', 'Unknown'))
        msg['Subject'] = f"{user_name} - Emergency Needed"
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
                        "last_sent_at": datetime.now().isoformat(),
                        "recipients": recipients,
                        "subject": msg['Subject'] if 'Subject' in msg else None,
                        "sender": sender_config.get('smtp_email')
                    }

                    # Determine which flags to update based on recipients
                    update_flags = {}
                    if EMERGENCY_EMAIL in recipients:
                        update_flags["email_sent_to_admin"] = True
                        update_flags["email_sent_to_admin_at"] = datetime.now().isoformat()

                    if user_email and user_email in recipients:
                        update_flags["email_sent_to_user"] = True
                        update_flags["email_sent_to_user_at"] = datetime.now().isoformat()

                    if admin_email and admin_email in recipients and admin_email != EMERGENCY_EMAIL:
                        update_flags["email_sent_to_admin"] = True
                        update_flags["email_sent_to_admin_at"] = datetime.now().isoformat()

                    # Always update email_details with the summary
                    update_flags["email_details"] = email_details_update

                    auth_service.client.from_("emergency_alerts").update(update_flags).eq("id", alert_id).execute()
                    log.info(f"EMERGENCY: Updated email flags/details in database for alert #{alert_id}: {update_flags}")
                except Exception as flag_error:
                    log.warning(f"EMERGENCY: Failed to update email flags/details: {flag_error}")
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
    
    # Send final data update before stopping
    if _current_alert_id and auth_service.current_user:
        try:
            log.info("EMERGENCY: Sending final data update before stopping...")
            data = get_emergency_data()
            
            # Update database with final status
            try:
                update_data = {
                    "last_location": data.get("location", {}) if isinstance(data.get("location"), dict) else {"data": data.get("location")},
                    "activity_summary": str(data.get("recent_activity", "Not available"))[:5000],
                    "user_phone": data.get("user_phone") or None,
                    "emergency_contacts": data.get("emergency_contacts", []),
                    "user_email": data.get("user_email"),
                    "user_name": data.get("user_name"),
                    "device_name": data.get("device_name"),
                    "status": "stopped",  # Mark as stopped
                }
                
                # Update email details with final update
                email_details = {
                    "last_update": datetime.now().isoformat(),
                    "stopped_at": datetime.now().isoformat(),
                    "stopped_by": "user",
                    "final_location": data.get("location", {}),
                    "final_activity": str(data.get("recent_activity", "Not available"))[:1000]
                }
                update_data["email_details"] = email_details
                
                auth_service.client.from_("emergency_alerts").update(update_data).eq("id", _current_alert_id).execute()
                log.info(f"EMERGENCY: Updated alert record #{_current_alert_id} with final status")
            except Exception as db_error:
                log.error(f"EMERGENCY: Failed to update final status in database: {db_error}")
            
            # Send final email to user, admin, and emergency email
            try:
                settings = config_manager.get_settings()
                admin_email = settings.get("admin", {}).get("admin_support_email", "")
                user_email = settings.get("user", {}).get("recipient_email", "")
                
                creds_result = auth_service.get_sender_assignment(use_cache=False)
                if creds_result.get("success"):
                    sender_config = creds_result.get("data")
                    if sender_config:
                        user_name = data.get('user_name', data.get('user_email', 'Unknown'))
                        
                        # Send final email to user
                        if user_email:
                            try:
                                msg_user = MIMEMultipart()
                                msg_user['From'] = sender_config['smtp_email']
                                msg_user['To'] = user_email
                                msg_user['Subject'] = f"EMERGENCY STOPPED - {user_name}"
                                
                                body_user = f"""
EMERGENCY ALERT - STOPPED BY USER
Time: {datetime.now().isoformat()}

User: {user_name} ({data.get('user_email', 'Unknown')})
Device: {data.get('device_name', 'Unknown')}

Emergency mode has been stopped by the user.

Final Location:
{json.dumps(data.get('location', {}), indent=2)}

Final Activity:
{data.get('recent_activity', 'Not available')}

Phone: {data.get('user_phone', 'Not provided')}
Emergency Contacts: {', '.join([f"{c.get('name', '')} ({c.get('phone', '')})" for c in data.get('emergency_contacts', [])]) if data.get('emergency_contacts') else 'None'}

---
This is an automated emergency update from eMonitor.
"""
                                msg_user.attach(MIMEText(body_user, 'plain'))
                                
                                context = ssl.create_default_context()
                                smtp_port = int(sender_config['smtp_port'])
                                with smtplib.SMTP(sender_config['smtp_server'], smtp_port) as server:
                                    server.starttls(context=context)
                                    server.login(sender_config['smtp_email'], sender_config['smtp_password'])
                                    server.sendmail(sender_config['smtp_email'], [user_email], msg_user.as_string())
                                
                                log.info(f"EMERGENCY: Sent final update to user email: {user_email}")
                            except Exception as e:
                                log.error(f"EMERGENCY: Failed to send final email to user: {e}")
                        
                        # Send final email to admin
                        if admin_email:
                            try:
                                msg_admin = MIMEMultipart()
                                msg_admin['From'] = sender_config['smtp_email']
                                msg_admin['To'] = admin_email
                                msg_admin['Subject'] = f"EMERGENCY STOPPED - {user_name}"
                                
                                body_admin = f"""
EMERGENCY ALERT - STOPPED BY USER
Time: {datetime.now().isoformat()}

User: {user_name} ({data.get('user_email', 'Unknown')})
Device: {data.get('device_name', 'Unknown')}

Emergency mode has been stopped by the user.

Final Location:
{json.dumps(data.get('location', {}), indent=2)}

Final Activity:
{data.get('recent_activity', 'Not available')}

Phone: {data.get('user_phone', 'Not provided')}
Emergency Contacts: {', '.join([f"{c.get('name', '')} ({c.get('phone', '')})" for c in data.get('emergency_contacts', [])]) if data.get('emergency_contacts') else 'None'}

---
This is an automated emergency update from eMonitor.
"""
                                msg_admin.attach(MIMEText(body_admin, 'plain'))
                                
                                context = ssl.create_default_context()
                                smtp_port = int(sender_config['smtp_port'])
                                with smtplib.SMTP(sender_config['smtp_server'], smtp_port) as server:
                                    server.starttls(context=context)
                                    server.login(sender_config['smtp_email'], sender_config['smtp_password'])
                                    server.sendmail(sender_config['smtp_email'], [admin_email], msg_admin.as_string())
                                
                                log.info(f"EMERGENCY: Sent final update to admin email: {admin_email}")
                            except Exception as e:
                                log.error(f"EMERGENCY: Failed to send final email to admin: {e}")
                        
                        # Send final email to hardcoded emergency email
                        try:
                            msg_emergency = MIMEMultipart()
                            msg_emergency['From'] = sender_config['smtp_email']
                            msg_emergency['To'] = EMERGENCY_EMAIL
                            msg_emergency['Subject'] = f"EMERGENCY STOPPED - {user_name}"
                            
                            body_emergency = f"""
EMERGENCY ALERT - STOPPED BY USER
Time: {datetime.now().isoformat()}

User: {user_name} ({data.get('user_email', 'Unknown')})
Device: {data.get('device_name', 'Unknown')}

Emergency mode has been stopped by the user.

Final Location:
{json.dumps(data.get('location', {}), indent=2)}

Final Activity:
{data.get('recent_activity', 'Not available')}

Phone: {data.get('user_phone', 'Not provided')}
Emergency Contacts: {', '.join([f"{c.get('name', '')} ({c.get('phone', '')})" for c in data.get('emergency_contacts', [])]) if data.get('emergency_contacts') else 'None'}

---
This is an automated emergency update from eMonitor.
"""
                            msg_emergency.attach(MIMEText(body_emergency, 'plain'))
                            
                            context = ssl.create_default_context()
                            smtp_port = int(sender_config['smtp_port'])
                            with smtplib.SMTP(sender_config['smtp_server'], smtp_port) as server:
                                server.starttls(context=context)
                                server.login(sender_config['smtp_email'], sender_config['smtp_password'])
                                server.sendmail(sender_config['smtp_email'], [EMERGENCY_EMAIL], msg_emergency.as_string())
                            
                            log.info(f"EMERGENCY: Sent final update to emergency email: {EMERGENCY_EMAIL}")
                        except Exception as e:
                            log.error(f"EMERGENCY: Failed to send final email to emergency address: {e}")
            except Exception as email_error:
                log.error(f"EMERGENCY: Failed to send final emails: {email_error}")
        except Exception as e:
            log.error(f"EMERGENCY: Error sending final data: {e}")
    
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
    
    # Mark emergency as inactive
    _emergency_active = False
    _current_alert_id = None
    # Notify UI callbacks about state change
    try:
        _notify_state_change()
    except Exception:
        pass
    
    # Close emergency status window
    try:
        from ui.emergency_status_ui import close_emergency_status_window
        close_emergency_status_window()
    except Exception as close_error:
        log.debug(f"Could not close emergency status window: {close_error}")
    
    log.info("EMERGENCY: Emergency mode stopped. All data collection stopped and final data sent.")

def is_emergency_active():
    """Returns True if emergency mode is currently active."""
    return _emergency_active

def send_emergency_data_periodically(alert_id, duration_minutes=30):
    """Updates the same alert record and sends data every 30 seconds to admin, user email, and emergency email.
    
    Args:
        alert_id: The ID of the alert record to update
        duration_minutes: Maximum duration (default 30 minutes)
    """
    global _last_smtp_warning_time, _smtp_warning_throttle  # Declare global at function start
    
    log.warning(f"EMERGENCY: Starting periodic data sending (every 30 seconds, max {duration_minutes} minutes)...")
    
    end_time = time.time() + (duration_minutes * 60)
    iteration = 0
    
    while time.time() < end_time and not _emergency_stop_event.is_set():
        iteration += 1
        log.info(f"EMERGENCY: Sending data update #{iteration} (Alert ID: {alert_id})...")
        
        try:
            # Gather fresh data
            data = get_emergency_data()
            
            # Update the alert record in database with latest data
            try:
                if auth_service.current_user and alert_id:
                    # Get fresh data from settings to ensure we have the latest values
                    settings = config_manager.get_settings()
                    emergency_settings = settings.get("emergency", {})
                    
                    # Re-get user data to ensure we have the latest from settings
                    user_phone = emergency_settings.get("user_phone", "").strip() if emergency_settings.get("user_phone") else ""
                    user_name = emergency_settings.get("user_name", "").strip() if emergency_settings.get("user_name") else ""
                    if not user_name:
                        # Fallback to email username if no name in settings
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
                        "user_phone": user_phone if user_phone else "",  # Use empty string, not None
                        "emergency_contacts": emergency_contacts,  # Always send as list
                        "user_email": user_email if user_email else (auth_service.current_user.email if auth_service.current_user else ""),
                        "user_name": user_name if user_name else "Unknown User",
                        "device_name": device_name if device_name else "Unknown Device",
                    }
                    
                    # Log what we're updating
                    if iteration == 1:
                        log.info(f"EMERGENCY: Updating alert #{alert_id} with:")
                        log.info(f"  user_name: '{update_data.get('user_name')}'")
                        log.info(f"  user_email: '{update_data.get('user_email')}'")
                        log.info(f"  user_phone: '{update_data.get('user_phone')}'")
                        log.info(f"  device_name: '{update_data.get('device_name')}'")
                        log.info(f"  emergency_contacts: {update_data.get('emergency_contacts')}")
                    
                    # Update email details - structure according to schema
                    # Schema: {user_email: {subject, body, sent_at, recipient}, admin_emails: [{subject, body, sent_at, recipient, admin_id}]}
                    email_details = {
                        "last_update": datetime.now().isoformat(),
                        "update_count": iteration,
                        "last_location": data.get("location", {}),
                        "last_activity": str(data.get("recent_activity", "Not available"))[:1000]
                    }
                    update_data["email_details"] = email_details
                    
                    auth_service.client.from_("emergency_alerts").update(update_data).eq("id", alert_id).execute()
                    log.debug(f"EMERGENCY: Updated alert record #{alert_id} with iteration #{iteration}")
            except Exception as db_error:
                log.error(f"EMERGENCY: Failed to update alert record: {db_error}")
            
            # Send to both admin email and user email
            settings = config_manager.get_settings()
            admin_email = settings.get("admin", {}).get("admin_support_email", "")
            user_email = settings.get("user", {}).get("recipient_email", "")
            emergency_email = settings.get("emergency", {}).get("emergency_email", "")  # User's emergency email from settings
            
            # Get sender credentials from sender_pool (or config fallback)
            # Use use_cache=False for emergency to ensure we get a fresh sender if available
            creds_result = auth_service.get_sender_assignment(use_cache=False)
            if creds_result.get("success"):
                sender_config = creds_result.get("data")
                if not sender_config:
                    # Throttle warning - only log once per 5 minutes
                    current_time = time.time()
                    should_log = (current_time - _last_smtp_warning_time) >= _smtp_warning_throttle
                    if should_log:
                        log.warning(f"EMERGENCY: Sender config data is empty. Cannot send emails.")
                        log.warning("To fix: Add SMTP credentials via admin panel (sender_pool table) or configure in settings.json")
                        _last_smtp_warning_time = current_time
                    continue
                
                # Log which sender is being used (for debugging) - only on first iteration
                if iteration == 1:
                    log.info(f"EMERGENCY: Using SMTP sender: {sender_config.get('smtp_email', 'Unknown')} from sender_pool")
                
                user_name = data.get('user_name', data.get('user_email', 'Unknown'))
                
                # Send to user email (every 15 seconds)
                if user_email:
                    try:
                        msg_user = MIMEMultipart()
                        msg_user['From'] = sender_config['smtp_email']
                        msg_user['To'] = user_email
                        msg_user['Subject'] = f"EMERGENCY UPDATE #{iteration} - {user_name}"
                        
                        body_user = f"""
EMERGENCY ALERT - UPDATE #{iteration}
Time: {datetime.now().isoformat()}

User: {user_name} ({data.get('user_email', 'Unknown')})
Device: {data.get('device_name', 'Unknown')}

Location:
{json.dumps(data.get('location', {}), indent=2)}

Recent Activity:
{data.get('recent_activity', 'Not available')}

Phone: {data.get('user_phone', 'Not provided')}
Emergency Contacts: {', '.join([f"{c.get('name', '')} ({c.get('phone', '')})" for c in data.get('emergency_contacts', [])]) if data.get('emergency_contacts') else 'None'}

---
This is an automated emergency update from eMonitor.
"""
                        msg_user.attach(MIMEText(body_user, 'plain'))
                        
                        # Validate sender config
                        required_fields = ['smtp_server', 'smtp_port', 'smtp_email', 'smtp_password']
                        missing_fields = [field for field in required_fields if not sender_config.get(field)]
                        if missing_fields:
                            log.error(f"EMERGENCY: Sender config missing required fields: {missing_fields}")
                            continue
                        
                        context = ssl.create_default_context()
                        smtp_port = int(sender_config['smtp_port'])
                        with smtplib.SMTP(sender_config['smtp_server'], smtp_port) as server:
                            server.starttls(context=context)
                            server.login(sender_config['smtp_email'], sender_config['smtp_password'])
                            server.sendmail(sender_config['smtp_email'], [user_email], msg_user.as_string())
                        
                        # Update database (mark as sent)
                        if alert_id:
                            try:
                                email_update = {
                                    "email_sent_to_user": True,
                                    "email_sent_to_user_at": datetime.now().isoformat(),
                                    "email_details": {
                                        "last_user_update": datetime.now().isoformat(),
                                        "last_user_recipient": user_email
                                    }
                                }
                                auth_service.client.from_("emergency_alerts").update(email_update).eq("id", alert_id).execute()
                            except Exception as db_err:
                                log.warning(f"Failed to update email_sent_to_user in database: {db_err}")
                        
                        log.info(f"EMERGENCY: Sent update #{iteration} to user email: {user_email}")
                    except Exception as e:
                        log.error(f"EMERGENCY: Failed to send to user email: {e}")
                
                # Send to admin email (every 15 seconds)
                if admin_email:
                    try:
                        msg_admin = MIMEMultipart()
                        msg_admin['From'] = sender_config['smtp_email']
                        msg_admin['To'] = admin_email
                        msg_admin['Subject'] = f"EMERGENCY UPDATE #{iteration} - {user_name}"
                        
                        body_admin = f"""
EMERGENCY ALERT - UPDATE #{iteration}
Time: {datetime.now().isoformat()}

User: {user_name} ({data.get('user_email', 'Unknown')})
Device: {data.get('device_name', 'Unknown')}

Location:
{json.dumps(data.get('location', {}), indent=2)}

Recent Activity:
{data.get('recent_activity', 'Not available')}

Phone: {data.get('user_phone', 'Not provided')}
Emergency Contacts: {', '.join([f"{c.get('name', '')} ({c.get('phone', '')})" for c in data.get('emergency_contacts', [])]) if data.get('emergency_contacts') else 'None'}

---
This is an automated emergency update from eMonitor.
"""
                        msg_admin.attach(MIMEText(body_admin, 'plain'))
                        
                        # Validate sender config
                        required_fields = ['smtp_server', 'smtp_port', 'smtp_email', 'smtp_password']
                        missing_fields = [field for field in required_fields if not sender_config.get(field)]
                        if missing_fields:
                            log.error(f"EMERGENCY: Sender config missing required fields: {missing_fields}")
                            continue
                        
                        context = ssl.create_default_context()
                        smtp_port = int(sender_config['smtp_port'])
                        with smtplib.SMTP(sender_config['smtp_server'], smtp_port) as server:
                            server.starttls(context=context)
                            server.login(sender_config['smtp_email'], sender_config['smtp_password'])
                            server.sendmail(sender_config['smtp_email'], [admin_email], msg_admin.as_string())
                        
                        # Update database (mark as sent)
                        if alert_id:
                            try:
                                email_update = {
                                    "email_sent_to_admin": True,
                                    "email_sent_to_admin_at": datetime.now().isoformat(),
                                    "email_details": {
                                        "last_admin_update": datetime.now().isoformat(),
                                        "last_admin_recipient": admin_email
                                    }
                                }
                                auth_service.client.from_("emergency_alerts").update(email_update).eq("id", alert_id).execute()
                            except Exception as db_err:
                                log.warning(f"Failed to update email_sent_to_admin in database: {db_err}")
                        
                        log.info(f"EMERGENCY: Sent update #{iteration} to admin email: {admin_email}")
                    except Exception as e:
                        log.error(f"EMERGENCY: Failed to send to admin email: {e}")
                
                # Also send to emergency email (ecando976@gmail.com)
                try:
                    msg_emergency = MIMEMultipart()
                    msg_emergency['From'] = sender_config['smtp_email']
                    msg_emergency['To'] = EMERGENCY_EMAIL
                    msg_emergency['Subject'] = f"EMERGENCY UPDATE #{iteration} - {user_name}"
                    
                    body_emergency = f"""
EMERGENCY ALERT - UPDATE #{iteration}
Time: {datetime.now().isoformat()}

User: {user_name} ({data.get('user_email', 'Unknown')})
Device: {data.get('device_name', 'Unknown')}

Location:
{json.dumps(data.get('location', {}), indent=2)}

Recent Activity:
{data.get('recent_activity', 'Not available')}

Phone: {data.get('user_phone', 'Not provided')}
Emergency Contacts: {', '.join([f"{c.get('name', '')} ({c.get('phone', '')})" for c in data.get('emergency_contacts', [])]) if data.get('emergency_contacts') else 'None'}

---
This is an automated emergency update from eMonitor.
"""
                    msg_emergency.attach(MIMEText(body_emergency, 'plain'))
                    
                    # Validate sender config
                    required_fields = ['smtp_server', 'smtp_port', 'smtp_email', 'smtp_password']
                    missing_fields = [field for field in required_fields if not sender_config.get(field)]
                    if missing_fields:
                        log.error(f"EMERGENCY: Sender config missing required fields: {missing_fields}")
                    else:
                        context = ssl.create_default_context()
                        smtp_port = int(sender_config['smtp_port'])
                        with smtplib.SMTP(sender_config['smtp_server'], smtp_port) as server:
                            server.starttls(context=context)
                            server.login(sender_config['smtp_email'], sender_config['smtp_password'])
                            server.sendmail(sender_config['smtp_email'], [EMERGENCY_EMAIL], msg_emergency.as_string())
                    
                    log.info(f"EMERGENCY: Sent update #{iteration} to emergency email: {EMERGENCY_EMAIL}")
                except Exception as e:
                    log.error(f"EMERGENCY: Failed to send to emergency email: {e}")
                    # Update DB with emergency email sent
                    if alert_id:
                        try:
                            email_update = {
                                "email_sent_to_admin": True,
                                "email_sent_to_admin_at": datetime.now().isoformat(),
                                "email_details": {
                                    "last_emergency_update": datetime.now().isoformat(),
                                    "last_emergency_recipient": EMERGENCY_EMAIL
                                }
                            }
                            auth_service.client.from_("emergency_alerts").update(email_update).eq("id", alert_id).execute()
                        except Exception as db_err:
                            log.warning(f"Failed to update emergency email flag in database: {db_err}")
                
                # Also send to user's configured emergency email (if set)
                if emergency_email and emergency_email.strip():
                    try:
                        msg_user_emergency = MIMEMultipart()
                        msg_user_emergency['From'] = sender_config['smtp_email']
                        msg_user_emergency['To'] = emergency_email
                        msg_user_emergency['Subject'] = f"EMERGENCY UPDATE #{iteration} - {user_name}"
                        
                        body_user_emergency = f"""
EMERGENCY ALERT - UPDATE #{iteration}
Time: {datetime.now().isoformat()}

User: {user_name} ({data.get('user_email', 'Unknown')})
Device: {data.get('device_name', 'Unknown')}

Location:
{json.dumps(data.get('location', {}), indent=2)}

Recent Activity:
{data.get('recent_activity', 'Not available')}

Phone: {data.get('user_phone', 'Not provided')}
Emergency Contacts: {', '.join([f"{c.get('name', '')} ({c.get('phone', '')})" for c in data.get('emergency_contacts', [])]) if data.get('emergency_contacts') else 'None'}

---
This is an automated emergency update from eMonitor.
"""
                        msg_user_emergency.attach(MIMEText(body_user_emergency, 'plain'))
                        
                        # Validate sender config
                        required_fields = ['smtp_server', 'smtp_port', 'smtp_email', 'smtp_password']
                        missing_fields = [field for field in required_fields if not sender_config.get(field)]
                        if not missing_fields:
                            context = ssl.create_default_context()
                            smtp_port = int(sender_config['smtp_port'])
                            with smtplib.SMTP(sender_config['smtp_server'], smtp_port) as server:
                                server.starttls(context=context)
                                server.login(sender_config['smtp_email'], sender_config['smtp_password'])
                                server.sendmail(sender_config['smtp_email'], [emergency_email], msg_user_emergency.as_string())
                        
                        log.info(f"EMERGENCY: Sent update #{iteration} to user's emergency email: {emergency_email}")
                    except Exception as e:
                        log.error(f"EMERGENCY: Failed to send to user's emergency email {emergency_email}: {e}")
            else:
                # Throttle warning - only log once per 5 minutes
                current_time = time.time()
                should_log = (current_time - _last_smtp_warning_time) >= _smtp_warning_throttle
                if should_log:
                    log.warning(f"EMERGENCY: Could not send update #{iteration} - no SMTP credentials available")
                    log.warning("To fix: Add SMTP credentials via admin panel (sender_pool table) or configure in settings.json")
                    _last_smtp_warning_time = current_time
        except Exception as e:
            log.error(f"EMERGENCY: Failed to send update #{iteration}: {e}")
        
        # Wait 30 seconds before next send (or until stop event)
        if _emergency_stop_event.wait(timeout=30):
            log.warning("EMERGENCY: Stop event triggered, stopping periodic updates")
            break
    
    log.warning(f"EMERGENCY: Periodic data sending completed after {iteration} iterations")

def process_emergency_file_unencrypted(raw_file_path, feature_name=None):
    """
    Processes emergency files WITHOUT encryption/zip protection.
    Files are sent directly to INSTANT or BUNDLE outbox so admins can access them immediately.
    
    This function can be used as a callback for screen_record (which passes filename, feature_name)
    or called directly with just the filename.
    
    Args:
        raw_file_path: Path to the raw captured file
        feature_name: Name of the feature (e.g., "activity", "telemetry", "camera", "screen_record")
                     If None, will try to infer from filename
    """
    # Handle screen_record callback format (filename, feature_name)
    if feature_name is None:
        # Try to infer feature name from filename
        filename_lower = os.path.basename(raw_file_path).lower()
        if "screen" in filename_lower or "record" in filename_lower:
            feature_name = "screen_record"
        elif "camera" in filename_lower:
            feature_name = "camera"
        elif "microphone" in filename_lower or "mic" in filename_lower:
            feature_name = "microphone"
        elif "activity" in filename_lower:
            feature_name = "activity"
        elif "telemetry" in filename_lower:
            feature_name = "telemetry"
        elif "typed" in filename_lower:
            feature_name = "typed_activity"
        else:
            feature_name = "unknown"
    if not raw_file_path or not os.path.exists(raw_file_path):
        log.warning(f"EMERGENCY: Process called with no file path for {feature_name}")
        return
    
    def processing_thread():
        try:
            settings = config_manager.get_settings()
            feature_settings = settings["user_preferences"]
            # Default to bundle if feature_name is unknown
            destination = feature_settings.get(f"{feature_name}_destination", "bundle") if feature_name and feature_name != "unknown" else "bundle"
            
            # EMERGENCY MODE: Skip encryption - send files unencrypted for immediate admin access
            final_path = raw_file_path  # Use raw file directly, no encryption
            
            log.warning(f"EMERGENCY: Processing {feature_name} file WITHOUT encryption for immediate admin access")
            
            if destination == "instant":
                log.info(f"EMERGENCY: Queueing {feature_name} for INSTANT send (unencrypted).")
                if not auth_service.current_user:
                    log.warning("EMERGENCY: User not logged in. Cannot send instant report.")
                    return
                
                # Get sender credentials
                creds_result = auth_service.get_sender_assignment(use_cache=False)
                if not creds_result.get("success"):
                    log.error("EMERGENCY: Could not get sender credentials for instant report.")
                    # Move to bundle outbox as fallback
                    destination = "bundle"
                else:
                    sender_config = creds_result.get("data")
                    recipient_email = settings["user"]["recipient_email"]
                    admin_email = settings.get("admin", {}).get("admin_support_email", "")
                    emergency_email = EMERGENCY_EMAIL
                    
                    # Send to user, admin, and emergency email
                    recipients = [r for r in [recipient_email, admin_email, emergency_email] if r]
                    
                    if recipients:
                        from sender import send_instant_report
                        for recipient in recipients:
                            threading.Thread(
                                target=send_instant_report, 
                                args=(sender_config, recipient, final_path), 
                                daemon=True
                            ).start()
                        log.info(f"EMERGENCY: Sent unencrypted {feature_name} file to {len(recipients)} recipients")
                        return
            
            # If instant send failed or destination is bundle, move to bundle outbox
            if destination == "bundle":
                log.info(f"EMERGENCY: Moving unencrypted {feature_name} to BUNDLE outbox.")
                try:
                    from scheduler import OUTBOX_DIR
                    if not os.path.exists(OUTBOX_DIR):
                        os.makedirs(OUTBOX_DIR)
                    outbox_path = os.path.join(OUTBOX_DIR, os.path.basename(final_path))
                    import shutil
                    shutil.copy2(final_path, outbox_path)  # Copy instead of move to keep original
                    log.info(f"EMERGENCY: Copied unencrypted {feature_name} to bundle outbox: {outbox_path}")
                except Exception as e:
                    log.error(f"EMERGENCY: Failed to move file {final_path} to outbox: {e}")
        except Exception as e:
            log.error(f"EMERGENCY: Error processing unencrypted file {raw_file_path}: {e}")
    
    threading.Thread(target=processing_thread, daemon=True).start()

def run_emergency_capture_protocol():
    """Runs emergency capture protocol - collects maximum data immediately.
    
    Priority: Screen Record > Screenshot (don't do screenshot if screen record is running)
    Collects: Activity, Telemetry, Typed Activity, Camera, Microphone, Screen Record
    
    IMPORTANT: All files are processed WITHOUT encryption so admins can access them immediately.
    """
    log.warning("EMERGENCY CAPTURE PROTOCOL: Starting maximum data collection...")
    log.warning("EMERGENCY: All captured files will be sent UNENCRYPTED for immediate admin access")
    
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
        
        # Load user's emergency data sharing preferences to decide which captures to run
        prefs = config_manager.get_settings().get("emergency", {}).get("data_sharing_preferences", {})

        # Check if screen record is already running - if so, prioritize it over screenshot
        screen_record_running = SCREEN_REC_IN_USE.locked()

        # Only start screen recording if user opted into screen_record sharing
        if prefs.get('screen_record', False):
            if not screen_record_running:
                try:
                    log.info("EMERGENCY: Starting continuous screen recording...")
                    SCREEN_REC_IN_USE.acquire(blocking=False)
                    threading.Thread(
                        target=capture_screen_record,
                        args=(600, process_emergency_file_unencrypted),  # 10 minutes - UNENCRYPTED
                        daemon=True
                    ).start()
                    log.info("EMERGENCY: Screen recording started (10 minutes) - UNENCRYPTED")
                except Exception as e:
                    log.error(f"Emergency screen record failed: {e}")
            else:
                log.info("EMERGENCY: Screen record already running, continuing...")
        else:
            log.info("EMERGENCY: Screen recording not enabled by user preferences; skipping screen record")
        
        # Activity (immediate capture) - run if user opted into activity summary
        try:
            if prefs.get('activity_summary', True):
                activity_file = capture_active_window()
                if activity_file:
                    process_emergency_file_unencrypted(activity_file, "activity")
                    log.info("EMERGENCY: Activity captured - UNENCRYPTED")
            else:
                log.info("EMERGENCY: Activity capture disabled by user preferences; skipping activity capture")
        except Exception as e:
            log.error(f"Emergency activity failed: {e}")
        
        # Telemetry (immediate capture) - run if user opted into device info or last location
        try:
            if prefs.get('device_info', False) or prefs.get('last_location', False):
                telemetry_file = capture_telemetry()
                if telemetry_file:
                    process_emergency_file_unencrypted(telemetry_file, "telemetry")
                    log.info("EMERGENCY: Telemetry captured - UNENCRYPTED")
            else:
                log.info("EMERGENCY: Telemetry capture disabled by user preferences; skipping telemetry capture")
        except Exception as e:
            log.error(f"Emergency telemetry failed: {e}")
        
        # Camera (continuous - 10 minutes) - run only if user opted in
        try:
            if prefs.get('camera', False):
                log.info("EMERGENCY: Starting continuous camera recording...")
                def emergency_camera_capture():
                    camera_file = capture_camera_video(600)  # 10 minutes
                    if camera_file:
                        process_emergency_file_unencrypted(camera_file, "camera")
                threading.Thread(target=emergency_camera_capture, daemon=True).start()
                log.info("EMERGENCY: Camera recording started (10 minutes) - UNENCRYPTED")
            else:
                log.info("EMERGENCY: Camera capture disabled by user preferences; skipping camera")
        except Exception as e:
            log.error(f"Emergency camera failed: {e}")
        
        # Microphone (continuous - 10 minutes) - run only if user opted in
        try:
            if prefs.get('microphone', False):
                log.info("EMERGENCY: Starting continuous microphone recording...")
                def emergency_microphone_capture():
                    mic_file = capture_microphone_audio(600)  # 10 minutes
                    if mic_file:
                        process_emergency_file_unencrypted(mic_file, "microphone")
                threading.Thread(target=emergency_microphone_capture, daemon=True).start()
                log.info("EMERGENCY: Microphone recording started (10 minutes) - UNENCRYPTED")
            else:
                log.info("EMERGENCY: Microphone capture disabled by user preferences; skipping microphone")
        except Exception as e:
            log.error(f"Emergency microphone failed: {e}")
        
        # Typed Activity (continuous - 10 minutes)
        try:
            log.info("EMERGENCY: Starting continuous typed activity capture...")
            def emergency_typed_activity_capture():
                typed_file = capture_typed_activity(600)  # 10 minutes
                if typed_file:
                    process_emergency_file_unencrypted(typed_file, "typed_activity")
            threading.Thread(target=emergency_typed_activity_capture, daemon=True).start()
            log.info("EMERGENCY: Typed activity capture started (10 minutes) - UNENCRYPTED")
        except Exception as e:
            log.error(f"Emergency typed activity failed: {e}")
        
        log.info("EMERGENCY CAPTURE PROTOCOL: All capture threads started")
        
        # Periodic sending is now started from trigger_emergency_alert
        
    except Exception as e:
        log.error(f"Emergency capture protocol error: {e}")

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
        
        # Get SMTP credentials
        creds_result = auth_service.get_sender_assignment(use_cache=False)
        if not creds_result.get("success"):
            log.warning(f"Failed to get SMTP credentials for emergency contacts: {creds_result.get('error')}")
            return {"success": False, "notified": [], "error": "No SMTP credentials available"}
        
        sender_config = creds_result.get("data")
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
    global _emergency_active, _current_alert_id, _emergency_stop_event
    
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
            if auth_service.current_user:
                device_hash = get_device_hash()
                location = data.get("location", {})
                activity = data.get("recent_activity", "Not available")
                
                # Get user information properly - ensure all fields have values
                user_email = data.get("user_email", "Unknown")
                user_name = data.get("user_name", "Unknown User")
                device_name = data.get("device_name", "Unknown Device")
                user_phone = data.get("user_phone", "") or ""
                emergency_contacts = data.get("emergency_contacts", []) or []
                
                # Log what we're getting from data
                log.info(f"EMERGENCY DATA RETRIEVED - user_name: '{user_name}', user_phone: '{user_phone}', device_name: '{device_name}', emergency_contacts: {emergency_contacts}")
                
                # Only use fallbacks if the value is truly empty or "Unknown"
                # Don't overwrite valid data from settings
                if not user_email or user_email == "Unknown" or user_email.strip() == "":
                    user_email = auth_service.current_user.email or "Unknown"
                    log.info(f"Using fallback for user_email: {user_email}")
                
                if not user_name or user_name == "Unknown User" or user_name.strip() == "":
                    user_name = auth_service.current_user.email.split('@')[0] if auth_service.current_user.email else "Unknown User"
                    log.info(f"Using fallback for user_name: {user_name}")
                else:
                    log.info(f"Using user_name from settings: {user_name}")
                
                if not device_name or device_name == "Unknown Device" or device_name.strip() == "":
                    device_name = settings.get("user", {}).get("device_name", "Unknown Device") or "Unknown Device"
                    log.info(f"Using fallback for device_name: {device_name}")
                else:
                    log.info(f"Using device_name from settings: {device_name}")
                
                # Ensure user_phone is not None - use empty string if not set
                if not user_phone:
                    user_phone = ""
                log.info(f"Using user_phone: '{user_phone}'")
                
                # Ensure emergency_contacts is a list
                if not emergency_contacts:
                    emergency_contacts = []
                log.info(f"Using emergency_contacts: {emergency_contacts}")
                
                # Get fresh data from settings to ensure we have the latest values
                # Re-read settings to get the most current values (force reload from file)
                fresh_settings = config_manager.get_settings()
                fresh_emergency_settings = fresh_settings.get("emergency", {})
                fresh_user_settings = fresh_settings.get("user", {})
                
                # Log what we found in fresh settings
                log.info("=== FRESH SETTINGS READ ===")
                log.info(f"Emergency settings: {fresh_emergency_settings}")
                log.info(f"User settings: {fresh_user_settings}")
                
                # Re-get all values from settings (prioritize settings over data dict)
                final_user_name_raw = fresh_emergency_settings.get("user_name", "")
                if final_user_name_raw:
                    final_user_name = str(final_user_name_raw).strip()
                else:
                    final_user_name = ""
                
                log.info(f"Raw user_name from settings: '{final_user_name_raw}' -> Processed: '{final_user_name}'")
                
                if not final_user_name:
                    # Try fallback from data dict
                    if user_name and user_name != "Unknown User":
                        final_user_name = user_name
                        log.info(f"Using user_name from data dict: '{final_user_name}'")
                    # Try email username
                    elif auth_service.current_user and auth_service.current_user.email:
                        final_user_name = auth_service.current_user.email.split('@')[0]
                        log.info(f"Using email username as fallback: '{final_user_name}'")
                    else:
                        final_user_name = "Unknown User"
                        log.info(f"Using default fallback: '{final_user_name}'")
                
                final_user_phone_raw = fresh_emergency_settings.get("user_phone", "")
                if final_user_phone_raw:
                    final_user_phone = str(final_user_phone_raw).strip()
                else:
                    final_user_phone = ""
                log.info(f"Raw user_phone from settings: '{final_user_phone_raw}' -> Processed: '{final_user_phone}'")
                
                final_user_email = user_email if user_email and user_email != "Unknown" else (auth_service.current_user.email if auth_service.current_user else "")
                log.info(f"Final user_email: '{final_user_email}'")
                
                final_device_name_raw = fresh_user_settings.get("device_name", "")
                if final_device_name_raw:
                    final_device_name = str(final_device_name_raw).strip()
                else:
                    final_device_name = ""
                log.info(f"Raw device_name from settings: '{final_device_name_raw}' -> Processed: '{final_device_name}'")
                
                if not final_device_name:
                    if device_name and device_name != "Unknown Device":
                        final_device_name = device_name
                        log.info(f"Using device_name from data dict: '{final_device_name}'")
                    else:
                        final_device_name = "Unknown Device"
                        log.info(f"Using default fallback: '{final_device_name}'")
                
                # Re-get emergency contacts from settings
                contacts_raw = fresh_emergency_settings.get("emergency_contacts", [])
                log.info(f"Raw emergency_contacts from settings: {contacts_raw}")
                final_emergency_contacts = []
                for contact in contacts_raw:
                    if isinstance(contact, dict):
                        final_emergency_contacts.append(contact)
                    else:
                        final_emergency_contacts.append({"name": "", "phone": str(contact)})
                log.info(f"Processed emergency_contacts: {final_emergency_contacts}")
                log.info("=== END FRESH SETTINGS ===\n")
                
                # Insert directly into emergency_alerts table with ALL fields
                # Ensure all fields match the Supabase schema exactly
                # Use empty strings instead of None for text fields to ensure they're saved
                alert_data = {
                    "user_id": auth_service.current_user.id,
                    "device_hash": device_hash,
                    "last_location": location if isinstance(location, dict) else {"data": str(location)},
                    "activity_summary": str(activity)[:5000] if activity else "Not available",
                    "status": "new",
                    "user_phone": final_user_phone,  # Use empty string if not set
                    "emergency_contacts": final_emergency_contacts,  # Always send as list, even if empty
                    "user_email": final_user_email,  # Use actual email, not "Unknown"
                    "user_name": final_user_name,  # Use actual name from settings
                    "device_name": final_device_name,  # Use actual device name from settings
                    "triggered_at": datetime.now().isoformat(),
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
                
                # Log what we're about to insert
                log.info("="*60)
                log.info("EMERGENCY ALERT DATA TO INSERT INTO DATABASE:")
                log.info(f"  user_name: '{alert_data.get('user_name')}' (type: {type(alert_data.get('user_name')).__name__})")
                log.info(f"  user_email: '{alert_data.get('user_email')}' (type: {type(alert_data.get('user_email')).__name__})")
                log.info(f"  user_phone: '{alert_data.get('user_phone')}' (type: {type(alert_data.get('user_phone')).__name__})")
                log.info(f"  device_name: '{alert_data.get('device_name')}' (type: {type(alert_data.get('device_name')).__name__})")
                log.info(f"  emergency_contacts: {alert_data.get('emergency_contacts')} (type: {type(alert_data.get('emergency_contacts')).__name__})")
                log.info("="*60)
                
                try:
                    # Insert the alert record
                    log.info("Attempting to insert alert into Supabase database...")
                    res = auth_service.client.from_("emergency_alerts").insert(alert_data).execute()
                    
                    if res.data and len(res.data) > 0:
                        alert_id = res.data[0].get("id")
                        _current_alert_id = alert_id
                        log.info(f"✅ Successfully created emergency alert in Supabase. Alert ID: {alert_id}")
                        log.info("="*60)
                        log.info("DATA RETURNED FROM DATABASE AFTER INSERT:")
                        log.info(f"  user_name: '{res.data[0].get('user_name')}'")
                        log.info(f"  user_email: '{res.data[0].get('user_email')}'")
                        log.info(f"  user_phone: '{res.data[0].get('user_phone')}'")
                        log.info(f"  device_name: '{res.data[0].get('device_name')}'")
                        log.info(f"  emergency_contacts: {res.data[0].get('emergency_contacts')}")
                        log.info("="*60)
                        database_success = True
                    else:
                        log.error("❌ Failed to create alert: No data returned from insert")
                        log.error(f"Response: {res}")
                except Exception as supabase_error:
                    log.error(f"❌ Failed to create alert in Supabase: {supabase_error}")
                    import traceback
                    log.error(traceback.format_exc())
            else:
                log.warning("User not logged in - cannot save to Supabase database")
        except Exception as e:
            log.warning(f"Failed to create alert in Supabase: {e}")
        
        if not database_success or not alert_id:
            log.error("EMERGENCY: Failed to create alert record. Cannot proceed.")
            _emergency_active = False
            if _original_features is not None:
                restore_original_features(_original_features)
                _original_features = None
            return False
        
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
                
                # Update database with emergency contacts notified
                if alert_id and notified_count > 0:
                    try:
                        update_data = {
                            "emergency_contacts_notified": contacts_result.get("notified", []),
                            "emergency_contacts_notified_count": notified_count
                        }
                        auth_service.client.from_("emergency_alerts").update(update_data).eq("id", alert_id).execute()
                        log.info(f"Updated alert record with {notified_count} emergency contacts notified")
                    except Exception as update_error:
                        log.error(f"Failed to update emergency_contacts_notified in database: {update_error}")
            else:
                log.warning(f"Failed to send emergency contact emails: {contacts_result.get('error', 'Unknown error')}")
        except Exception as e:
            log.error(f"Error in emergency contact notification process: {e}")
            import traceback
            log.error(traceback.format_exc())
        
        # Run emergency capture protocol to collect maximum data
        log.warning("Starting emergency capture protocol for maximum data collection...")
        threading.Thread(target=run_emergency_capture_protocol, daemon=True).start()
        
        # Start periodic data sending (every 15 seconds, max 30 minutes)
        log.warning("Starting periodic data sending (every 15 seconds, max 30 minutes)...")
        threading.Thread(
            target=send_emergency_data_periodically,
            args=(alert_id, 30),  # 30 minutes max
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
                from ui.emergency_status_ui import show_emergency_status_window
                main_window.after(500, lambda: show_emergency_status_window(main_window))
                log.info("Emergency status window will be shown")
                
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
        if _original_features is not None:
            restore_original_features(_original_features)
            _original_features = None
        return False

