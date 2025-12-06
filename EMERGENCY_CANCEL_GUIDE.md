# Emergency Mode Cancel Feature - Complete Guide

## Overview
The emergency cancel feature allows users to stop emergency mode at any time after it's been triggered. There are **three ways** to cancel/stop emergency mode:

1. **Emergency Status Window (Primary)**
2. **Dashboard Button**
3. **Emergency Contacts UI (to disable the feature)**

---

## How Emergency Mode Works

### 1. Triggering Emergency
Users can trigger emergency mode by:
- Clicking the red **"🚨 EMERGENCY ALERT 🚨"** button on the Dashboard
- Using the hotkey (default: `Ctrl+Alt+E`)

### 2. Grace Period
After triggering, a **Grace Period Window** appears with a countdown (default: 15 seconds).
- Shows: "Emergency Alert Triggered!"
- Large countdown timer
- **Cancel button** to abort before sending
- If countdown reaches 0, emergency is activated and emails are sent

### 3. Emergency Mode Active
Once the grace period expires, **Emergency Status Window** appears showing:
- "*** EMERGENCY MODE ACTIVE ***" title
- Information about what data is being collected
- **Large orange "STOP" button** to cancel emergency
- Timer showing how long emergency has been active

---

## Three Ways to Cancel Emergency Mode

### Method 1: Emergency Status Window (Recommended)
**How to access:**
- Appears automatically when emergency mode is activated
- Large persistent window with dark red background
- Always on top and non-closable (forces user attention)

**To cancel:**
1. Click the large **orange "STOP" button** with text: **"[STOP] CANCEL / STOP EMERGENCY MODE [STOP]"**
2. Confirmation dialog will appear asking: "Are you sure you want to stop emergency mode?"
3. Click **"Yes"** to confirm
4. Message: "Emergency mode has been stopped successfully"
5. Window automatically closes

**What happens when you stop:**
- ✓ All data collection stops immediately
- ✓ Final data update is sent to the database
- ✓ Monitoring features return to their normal settings
- ✓ Dashboard button returns to showing "🚨 EMERGENCY ALERT 🚨"

---

### Method 2: Dashboard Button
**How to access:**
- Go to the main Dashboard
- After emergency is triggered, the red emergency button is replaced with an **orange "STOP" button**

**To cancel:**
1. Locate the **orange "[STOP] CANCEL EMERGENCY MODE [STOP]"** button
2. Click it
3. Confirmation dialog appears
4. Click **"Yes"** to confirm
5. Dashboard button returns to normal

---

### Method 3: Disable Emergency Feature (Settings)
**How to access:**
- Open Settings page
- Go to **"Emergency Alert Settings"** section
- Uncheck the **"Enable Emergency Alert"** checkbox

**Effect:**
- Emergency feature is disabled until re-enabled
- Prevents accidental triggers
- Existing emergency mode will continue (doesn't stop active emergency)

---

## What Gets Stopped

When you click "STOP", the following happens:

| Component | Action |
|-----------|--------|
| **Email Sending** | Stops sending data to emergency contacts |
| **Screen Recording** | Stops recording (if enabled) |
| **Camera Capture** | Stops capturing (if enabled) |
| **Microphone Recording** | Stops recording (if enabled) |
| **Activity Monitoring** | Stops monitoring keystrokes/activity |
| **Telemetry** | Stops collecting location data |
| **Database Updates** | Sends final summary and updates `status` field to "completed" |

---

## Database Updates on Stop

When emergency is stopped, these fields are updated in the `emergency_alerts` table:

```sql
{
  "status": "completed",
  "stopped_at": "2025-12-06T14:30:45.123Z",
  "email_details": {
    "admin_email": "sent_successfully",
    "user_email": "sent_successfully",
    "emergency_contacts_notified": [
      {"name": "Contact Name", "email": "contact@example.com", "status": "sent"}
    ]
  },
  "data_shared": {
    "screenshot": true,
    "device_info": true,
    "last_location": true,
    "activity_summary": true,
    "logs": true,
    "camera": true,
    "microphone": true,
    "screen_record": true
  }
}
```

---

## Visual Guide

### Emergency Status Window
```
╔════════════════════════════════════════════════════════════╗
║      *** EMERGENCY MODE ACTIVE ***                        ║
║                                                            ║
║  Emergency alert has been triggered and is actively       ║
║  collecting data.                                         ║
║                                                            ║
║  Data is being sent every 15 seconds to:                  ║
║  • Emergency contacts                                     ║
║  • Admin email                                            ║
║  • Emergency email                                        ║
║                                                            ║
║  All monitoring features are enabled:                     ║
║  • Screen recording                                       ║
║  • Camera capture                                         ║
║  • Activity monitoring                                    ║
║  • Location tracking                                      ║
║  • Telemetry data                                         ║
║                                                            ║
║         Active for: 5 minutes 23 seconds                  ║
║         ═════════════════════════════════════             ║
║     [STOP] CANCEL / STOP EMERGENCY MODE [STOP]           ║
║        ═════════════════════════════════════              ║
║  !!! Click the button above to cancel and stop !!!        ║
╚════════════════════════════════════════════════════════════╝
```

### Dashboard with Active Emergency
```
Normal State:
  [🚨 EMERGENCY ALERT 🚨]
  Press this button or use Ctrl+Alt+E to send an emergency alert

Emergency Active State:
  [[STOP] CANCEL EMERGENCY MODE [STOP]]
  (Orange button replaces the red one)
```

---

## Troubleshooting

### "Emergency Status Window doesn't appear"
**Solutions:**
1. Check that emergency mode was actually activated (check logs)
2. The window might be hidden behind another window - click Dashboard
3. Check that the grace period countdown completed (didn't click Cancel during countdown)

### "Can't close the Emergency Status Window"
**Expected behavior:**
- The window is intentionally non-closable until emergency is stopped
- Click the orange STOP button to close it properly
- If button doesn't work, use Dashboard button as backup

### "Stop button isn't working"
**Solutions:**
1. Check logs for errors: `tail -f app.log | grep -i "emergency"`
2. Verify database connection is active
3. Try using Dashboard button instead
4. Restart the application if issues persist

### "Dashboard button shows green instead of orange"
**Status:**
- Green = Emergency was successfully stopped
- Orange = Emergency is still active and can be stopped
- Red = Emergency alert ready to trigger

---

## Emergency Contact Configuration

To receive emergency alerts, contacts must be configured in Settings:

1. Go to **Settings** → **Emergency Alert Settings**
2. Click **"Add Emergency Contact"**
3. Fill in:
   - **Name**: Contact's name
   - **Phone**: Phone number
   - **Email**: Email address
   - **Relationship**: Relationship to user (e.g., "Parent", "Friend", "Medical Provider")
4. Click **"Add"**
5. Contact will receive email notifications when emergency is triggered

---

## Data Sharing Settings

Control what data is collected during emergency mode:

In **Settings** → **Emergency Alert Settings**, enable/disable:
- ✓ Screenshot
- ✓ Device Information
- ✓ Last Known Location
- ✓ Activity Summary
- ✓ Application Logs
- ✓ Camera Capture
- ✓ Microphone Recording
- ✓ Screen Recording

**Note:** During emergency, ONLY the enabled options will be captured and sent.

---

## Integration Points

### Code Files
- `emergency_alert_manager.py` - Core stop logic (`stop_emergency_mode()`)
- `alert_manager.py` - Triggers emergency and shows status window
- `ui/emergency_status_ui.py` - Cancel button UI
- `ui/dashboard_ui.py` - Dashboard cancel button
- `ui/grace_period_ui.py` - Grace period countdown

### Database Tables
- `emergency_alerts` - Stores emergency records with status

### Configuration
- `config.py` - Emergency settings defaults
- `settings.json` - User's emergency preferences (local)

---

## Security Notes

- ✓ All exception traces are logged at DEBUG level (not shown to user)
- ✓ Error messages are generic to avoid leaking sensitive paths
- ✓ Emergency contacts data is sanitized before sending
- ✓ Stop operations are atomic (all-or-nothing)
- ✓ Database updates are transactional

---

## Testing Emergency Cancel

### Quick Test Flow
1. **Open application** - Dashboard should show
2. **Click "🚨 EMERGENCY ALERT 🚨" button**
3. **Wait for grace period countdown** (default: 15 seconds)
4. **Confirm** in the "Send Alert?" dialog (don't cancel)
5. **Wait for emergency to activate** - Status window should appear
6. **Click orange "STOP" button** on status window
7. **Confirm stop** in confirmation dialog
8. **Verify:**
   - Status window closes
   - Dashboard button returns to red (🚨 EMERGENCY ALERT 🚨)
   - Check logs for "Emergency mode stopped successfully"
   - Check database for status="completed"

---

## Recent Changes (v1.1)

### What's Fixed
- ✅ Emergency Status Window now automatically shows when emergency is triggered
- ✅ Cancel buttons now properly connected to `stop_emergency_mode()` function
- ✅ Grace Period window automatically closes after emergency is sent
- ✅ Error messages are sanitized (no sensitive paths/exceptions)
- ✅ Dashboard button state updates properly when emergency starts/stops
- ✅ Emergency capture protocol respects user's data-sharing preferences

### Known Issues
- None currently (all reported issues fixed)

---

## Support

For issues or questions:
1. Check application logs: `tail -f app.log`
2. Review this guide for common troubleshooting
3. Enable DEBUG logging: `config_manager.set_debug(True)`
4. Contact admin: ecando976@gmail.com

---

**Last Updated:** December 6, 2025
**Version:** 1.1
**Status:** ✅ All emergency cancel features working
