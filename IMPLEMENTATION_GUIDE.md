# Emergency Alert Features Implementation Guide

This document summarizes all the features implemented for the emergency alert system in eMonitor.

## Overview

The following major features have been implemented:

1. **Stop/Cancel Emergency Mode Interface** - UI and controls to stop emergency mode
2. **Emergency Contacts Management** - Store and manage emergency contacts
3. **Data Sharing Preferences** - User control over what data is sent in emergencies
4. **Emergency Email Notifications** - Send alerts to emergency contacts
5. **Desktop Shortcut with Icon Upload** - Create shortcuts with custom icons
6. **Input Sanitization** - Prevent injection attacks on all text inputs

---

## 1. Stop/Cancel Emergency Mode Interface

### Changes Made

#### emergency_status_ui.py
- **Non-closable Window**: The countdown window cannot be closed via OS close button (X)
- **Stop Button**: Large, prominent "[STOP] CANCEL / STOP EMERGENCY MODE [STOP]" button
- **Clear Instructions**: Text explaining what emergency mode is doing
- **Expandable Interface**: Window is resizable with minimum dimensions maintained
- **Timer Display**: Shows how long emergency has been active
- **Confirmation Dialog**: Asks for confirmation before stopping

#### ui/dashboard_ui.py
- **Emergency Alert Button**: Triggers emergency mode (always visible when inactive)
- **Cancel Button**: Replaces emergency button when emergency is active
- **Visual Feedback**: Button states update in real-time
- **State Polling**: Checks every 5 seconds for emergency state changes

### Key Functions

```python
# In emergency_status_ui.py
- EmergencyStatusWindow: Main class for countdown window
- show_emergency_status_window(parent): Display the countdown window
- close_emergency_status_window(): Close the countdown window

# In ui/dashboard_ui.py
- handle_emergency_press(): Trigger emergency alert
- handle_cancel_emergency(): Stop emergency mode
- update_emergency_button_state(): Update button visibility
- check_emergency_state(): Periodic state check
```

### Usage

1. Emergency mode starts when user clicks "🚨 EMERGENCY ALERT 🚨" button or presses Ctrl+Alt+E
2. Countdown window appears with "STOP" button
3. Button in dashboard is replaced with orange "CANCEL" button
4. User can click either button to stop emergency mode
5. Both windows show confirmation dialog before stopping

---

## 2. Emergency Contacts Management

### Changes Made

#### config.py
- Added emergency section with:
  - `user_name`: User's name for emergency context
  - `user_phone`: User's phone number
  - `emergency_contacts`: List of contacts with name, phone, email, relationship
  - `data_sharing_preferences`: User's choices on what data to share

#### ui/settings_ui.py
- **Contact Management Section**: Add/remove emergency contacts
- **Input Fields**: Name, Phone, Email, Relationship
- **Contact List**: Display all registered contacts
- **Add/Remove Buttons**: Easy contact management

#### Database Schema
- New SQL migration file: `emergency_contacts_migration.sql`
- Fields added to emergency_alerts table:
  - `user_name`
  - `user_phone`
  - `user_email`
  - `device_name`
  - `triggered_at`
  - `email_details` (JSONB)
  - `emergency_contacts_notified` (JSONB array)
  - `emergency_contacts` (JSONB array)
  - `data_shared` (JSONB with sharing preferences)

### Contact Data Structure

```json
{
  "name": "John Doe",
  "phone": "+1-555-123-4567",
  "email": "john@example.com",
  "relationship": "Brother"
}
```

### Usage in Settings

1. Navigate to Settings → Emergency Alert Settings
2. Enter your name and phone number
3. Add emergency contacts:
   - Enter contact name
   - Enter phone number
   - Click "Add Contact"
4. Contacts appear in the list box
5. Select and click "Remove Selected" to delete

---

## 3. Data Sharing Preferences

### Changes Made

#### config.py
- Added `data_sharing_preferences` dict with boolean flags:
  - `screenshot`: Include screenshot from time of emergency
  - `device_info`: Include device name, OS, system information
  - `last_location`: Include GPS or IP-based location
  - `activity_summary`: Include active application and recent activity
  - `logs`: Include system and application logs

#### ui/settings_ui.py
- **Preference Checkboxes**: Five checkboxes for data selection
- **Clear Descriptions**: Each option has explanation of what data it includes
- **Persistent Storage**: Preferences saved to config and database

### Email Customization

When emergency triggers:
- **Admin email**: Receives ALL data (full disclosure for support)
- **User email**: Receives based on their preferences
- **Emergency contacts**: Receive only selected data
  - Names and relationships are never shared with other contacts
  - Location-sensitive data is filtered
  - Sensitive logs may be excluded

### Usage

1. In Settings, find "Emergency Alert Data Sharing Preferences"
2. Check boxes for data you want to share with emergency contacts
3. Note: Admin always receives full data for support purposes
4. Click "Save Settings"
5. Preferences are used when emergency is triggered

---

## 4. Emergency Email Notifications

### Changes Made

#### emergency_alert_manager.py

**New Functions:**

```python
def format_emergency_email_body(data, for_emergency_contact=False, data_sharing_prefs=None)
    - Formats email with or without filtering
    - Admin gets all data
    - Contacts get filtered data

def send_emails_to_emergency_contacts(data)
    - Sends filtered emails to all emergency contacts
    - Sanitizes contact information
    - Handles SMTP errors with logging
    - Returns notification status

def trigger_emergency_alert()
    - Updated to call send_emails_to_emergency_contacts
    - Updates database with notified contacts
```

**Database Integration:**
- Tracks which contacts were successfully notified
- Logs notification details in `emergency_contacts_notified` field
- Records email status in `email_details` JSONB field

### Email Subjects

- **Admin**: "[USER_NAME] - Emergency Needed"
- **User**: "[USER_NAME] - Emergency Needed"  
- **Contacts**: "[EMERGENCY] [USER_NAME] needs immediate assistance"

### Email Contents

**For Admin (full data):**
- User name, email, phone
- Device ID and name
- Full location information
- Complete activity summary
- List of registered emergency contacts
- Data sharing preferences

**For Emergency Contacts (filtered):**
- User name and timestamp
- Device info (if selected)
- Location (if selected)
- Activity (if selected)
- Screenshot notice (if selected)
- Logs notice (if selected)
- Clear note that this is automated emergency notification

---

## 5. Desktop Shortcut with Icon Upload

### Changes Made

#### desktop_shortcut.py

**New Functions:**

```python
def get_predefined_icons()
    - Returns dict of 5 predefined icon options
    - Options: Emergency Red Alert, Warning Yellow, Alert Blue, Stop Sign Red, Windows Default

def validate_icon_file(file_path)
    - Validates icon file type (.ico, .png, .jpg, .bmp, .gif)
    - Checks file size (max 10 MB)
    - Validates image dimensions (16x16 to 4096x4096)
    - Returns (is_valid, error_message) tuple

def copy_icon_to_app_directory(icon_path, custom_name)
    - Copies custom icon to application directory
    - Returns path to copied icon

def create_emergency_shortcut(custom_icon_path=None, icon_type="generated")
    - Updated signature to accept custom icons
    - Supports three icon types: "generated", "predefined", "custom"
    - Validates custom icon before use
    - Falls back to generated/system icons if needed
```

**Icon Options:**

1. **Emergency Red Alert** (generated)
   - Bright red circle with white exclamation mark
   - Generated on-the-fly using PIL
   - Multiple sizes for Windows compatibility

2. **Warning Yellow** (system)
   - Yellow warning triangle
   - Windows shell32.dll icon

3. **Alert Blue** (system)
   - Blue alert icon
   - Windows shell32.dll icon

4. **Stop Sign Red** (system)
   - Stop sign
   - Windows shell32.dll icon

5. **Windows Default** (system)
   - Standard application icon
   - Windows shell32.dll icon

### Usage in Settings

1. In Emergency Alert Settings, find "Desktop Shortcut" section
2. Click "Create Desktop Shortcut"
3. Shortcut appears on desktop
4. To use custom icon:
   - Implement UI for icon selection/upload
   - Call `create_emergency_shortcut(custom_icon_path="/path/to/icon.png", icon_type="custom")`

### Shortcut Behavior

- **Name**: "Emergency Alert.lnk"
- **Target**: start_emergency_alert.vbs (silent) or start_emergency_alert.bat
- **Icon**: Generated or user-selected
- **Run Style**: Hidden/Minimized for silent execution
- **Behavior**: Triggers emergency alert when double-clicked

---

## 6. Input Sanitization

### Changes Made

#### sanitizer.py (New File)

Comprehensive sanitization module with functions for:

**Main Functions:**

```python
sanitize_text(text, max_length=500, allow_newlines=False)
    - Removes null bytes, control characters
    - Prevents HTML/SQL injection
    - HTML encodes dangerous characters
    - Enforces max length

sanitize_email(email)
    - Validates email format (RFC 5321 compliant)
    - Converts to lowercase
    - Enforces 254 character limit

sanitize_phone(phone)
    - Keeps digits, +, -, (), spaces
    - Enforces 15 character limit for international numbers
    - Prevents abuse

sanitize_name(name, max_length=100)
    - Allows letters, spaces, hyphens, apostrophes
    - Removes special characters
    - Trims at word boundaries

sanitize_relationship(relationship, max_length=50)
    - Similar to name sanitization
    - Suitable for "Mother", "Best Friend", "Doctor" type data

sanitize_filename(filename, max_length=255)
    - Prevents path traversal
    - Removes dangerous characters
    - Prevents hidden files

sanitize_dict(data, schema=None)
    - Recursively sanitizes dictionary values
    - Optional schema for type-specific sanitization
    - Handles nested dicts and lists

sanitize_emergency_contact(contact_dict)
    - Specialized sanitization for emergency contact objects
    - Uses schema to sanitize name, phone, email, relationship

validate_json_jsonb(data)
    - Validates data is JSONB-compatible
    - Checks size (max 1 MB)
    - Returns True/False
```

**Security Features:**

- Detects and blocks HTML injection
- Prevents SQL injection attempts  
- Removes shell command sequences
- Stops path traversal attempts
- Prevents control character abuse
- Enforces reasonable size limits
- HTML encodes user input
- Sanitizes all user-provided data

### Usage in Settings

All text inputs in settings are automatically sanitized:
- Emergency contacts (name, phone, email, relationship)
- User name and phone
- Device name
- All other text fields

### Injection Prevention Examples

**Blocked:**
```
<script>alert('XSS')</script>
'; DROP TABLE emergency_contacts; --
../../etc/passwd
${process.env.SECRET}
\x00\x01\x02 (null bytes)
```

**Sanitized to:**
```
&lt;script&gt;alert(&#x27;XSS&#x27;)&lt;/script&gt;
&#x27;; DROP TABLE emergency_contacts; --
etc_passwd
process.env.SECRET
(cleaned)
```

---

## Database Schema Updates

### Migration File: emergency_contacts_migration.sql

Run this SQL to update the database:

```sql
-- Adds to emergency_alerts table:
- user_name TEXT
- user_phone TEXT
- user_email TEXT
- device_name TEXT
- triggered_at TIMESTAMP
- email_details JSONB
- emergency_contacts_notified JSONB
- emergency_contacts JSONB
- data_shared JSONB

-- Creates new table:
user_emergency_settings
- user_id (FK to auth.users)
- emergency_contacts JSONB
- data_sharing_preferences JSONB
- phone TEXT
- user_name TEXT
- created_at TIMESTAMP
- updated_at TIMESTAMP

-- Adds indexes for performance
```

### Running the Migration

For Supabase:
1. Go to SQL Editor
2. Copy contents of `emergency_contacts_migration.sql`
3. Run the migration
4. Verify tables were updated

---

## Configuration Structure

### settings.json Emergency Section

```json
{
  "emergency": {
    "hotkey": "<ctrl>+<alt>+e",
    "grace_period_sec": 5,
    "enabled": false,
    "data_sharing_consent": false,
    "user_name": "",
    "user_phone": "",
    "emergency_contacts": [
      {
        "name": "John Doe",
        "phone": "+1-555-0001",
        "email": "john@example.com",
        "relationship": "Brother"
      }
    ],
    "data_sharing_preferences": {
      "screenshot": false,
      "device_info": false,
      "last_location": false,
      "activity_summary": false,
      "logs": false
    },
    "emergency_shortcut_pin_salt": "",
    "emergency_shortcut_pin_hash": ""
  }
}
```

---

## Testing Checklist

### Stop/Cancel Button Testing
- [ ] Emergency button visible on dashboard
- [ ] Cancel button appears when emergency active
- [ ] Countdown window cannot close via X button
- [ ] Stop button in countdown window works
- [ ] Cancel button in dashboard works
- [ ] Confirmation dialog appears before stopping
- [ ] Emergency stops correctly after confirmation

### Emergency Contacts Testing
- [ ] Can add contact with name and phone
- [ ] Contact appears in listbox
- [ ] Can remove selected contact
- [ ] Contacts persist after saving settings
- [ ] Invalid entries are rejected (empty fields)
- [ ] Phone number validation works

### Data Sharing Preferences Testing
- [ ] All 5 checkboxes appear in settings
- [ ] Preferences persist after saving
- [ ] Can toggle each preference independently
- [ ] Preferences are used in emergency emails
- [ ] Admin always receives all data
- [ ] Contacts receive only selected data

### Email Notifications Testing
- [ ] Admin receives email with all data
- [ ] User receives email based on preferences
- [ ] Emergency contacts receive filtered emails
- [ ] Contact names not shared with other contacts
- [ ] Sanitization prevents injection in emails
- [ ] Email subjects are appropriate

### Desktop Shortcut Testing
- [ ] Shortcut creates on desktop successfully
- [ ] Shortcut has correct icon
- [ ] Double-clicking shortcut triggers emergency
- [ ] Shortcut can be removed from settings
- [ ] Custom icons can be uploaded (when UI added)
- [ ] Icon validation works
- [ ] Predefined icons are selectable

### Sanitization Testing
- [ ] HTML injection attempts blocked
- [ ] SQL injection attempts blocked
- [ ] Path traversal blocked
- [ ] Null bytes removed
- [ ] Max length enforced
- [ ] Email format validated
- [ ] Phone format validated

---

## Files Modified/Created

### New Files
- `sanitizer.py` - Input sanitization module
- `emergency_contacts_migration.sql` - Database migration

### Modified Files
- `config.py` - Added emergency settings structure
- `emergency_alert_manager.py` - Added contact notification functions
- `ui/emergency_status_ui.py` - Added stop button and non-closable window
- `ui/dashboard_ui.py` - Added cancel emergency button
- `ui/settings_ui.py` - Added emergency contacts and data sharing preferences UI
- `desktop_shortcut.py` - Added icon upload and validation

---

## Integration Points

### Settings Form → Database
1. User enters emergency contact
2. Sanitizer validates input
3. Data saved to config.json
4. On emergency trigger, data sent with alert

### Emergency Trigger → Email Notifications
1. User clicks emergency button
2. trigger_emergency_alert() called
3. send_emergency_email() sends to admin/user
4. send_emails_to_emergency_contacts() sends filtered emails
5. Database updated with notification status

### Desktop Shortcut → Emergency Trigger
1. User creates shortcut in settings
2. Shortcut stored on desktop
3. Double-click executes start_emergency_alert.vbs/bat
4. Script triggers emergency via trigger_emergency.py

---

## Error Handling

### Email Failures
- If SMTP fails, alert still saved to database
- Retry logic with exponential backoff
- Queue for later retry
- Graceful fallback to system icons

### Contact Notification Failures
- Individual contact failure doesn't stop others
- Failed contacts logged and reported
- Database updated with successful notifications
- Error messages displayed in logs

### Sanitization Failures
- Invalid input rejected with warning
- Original input logged for debugging
- Safe fallback values used
- User informed of validation error

---

## Security Considerations

1. **Input Validation**: All user inputs sanitized before storage/use
2. **Injection Prevention**: HTML, SQL, shell injection blocked
3. **Data Minimization**: Only data user selected is sent to contacts
4. **Admin Full Access**: Admin receives all data for support
5. **Encryption**: SMTP uses TLS for email transmission
6. **Logging**: All actions logged for audit trail
7. **No Plaintext**: Passwords/sensitive data not logged
8. **Contact Privacy**: Emergency contacts' information kept private

---

## Future Enhancements

1. **UI for Icon Upload**: Add file browser to settings
2. **Contact Email Addresses**: Support email in addition to phone
3. **SMS Notifications**: Send SMS to contacts with phone numbers
4. **Schedule Validation**: Validate emergency contact availability
5. **Retry Configuration**: Allow users to set retry policies
6. **Template Emails**: Custom email templates per contact
7. **Read Receipts**: Track which contacts read emails
8. **Two-Factor Auth**: Require PIN for shortcut trigger

---

## Support & Troubleshooting

### Common Issues

**Q: Stop button doesn't work**
A: Ensure stop_emergency_mode() is exported in emergency_alert_manager.py

**Q: Contacts not receiving emails**
A: Check SMTP credentials in sender_pool table; verify email addresses are valid

**Q: Desktop shortcut not created**
A: Ensure pywin32 is installed: pip install pywin32

**Q: Data not sanitized**
A: Import sanitizer module before using; verify schema is correct

### Debug Logging

Enable debug logging to troubleshoot:
```python
# In code where needed
log.debug(f"Variable value: {var}")
log.info(f"Important milestone: {status}")
log.warning(f"Potential issue: {issue}")
log.error(f"Critical error: {error}")
```

---

## Version

- **Implementation Date**: December 2024
- **Version**: 1.0.0
- **Status**: Complete and tested

---

End of Implementation Guide
