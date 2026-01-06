# Emergency Mode - Complete System Overview

## 🚨 How Emergency Mode Works

### When You Click "TURN ON EMERGENCY"

1. **Subscription Bypass** ✅
   - **ALL subscription restrictions are removed**
   - The system enables ALL features temporarily:
     - Camera
     - Microphone  
     - Screen Recording
     - Activity Tracking
     - Location Tracking
     - Telemetry
   - This happens automatically - you don't need to do anything

2. **Grace Period Window Opens** (5 seconds default)
   - Countdown timer shows
   - You can cancel if it was accidental
   - After countdown → Emergency mode ACTIVATES

3. **Emergency Mode ACTIVE**
   - Grace period window transforms to "Emergency Control Panel"
   - Shows: "✓ EMERGENCY MODE IS NOW ACTIVE ✓"
   - Button changes to: "🛑 STOP EMERGENCY MODE 🛑"
   - Window stays on top (you can minimize it)

### What Data Gets Collected

The system collects data based on **YOUR settings** in Emergency Alert settings:

**Data Sharing Preferences** (you control these):
- ✅ Screenshot
- ✅ Device Info
- ✅ Last Location
- ✅ Activity Summary
- ✅ Logs
- ✅ Camera (30-second video clips)
- ✅ Microphone (30-second audio clips)
- ✅ Screen Record (30-second video clips)

**Collection Schedule**:
- Every 30 seconds, the system captures all enabled data types
- All data is **bundled into ONE email** per 30-second interval
- Sent to ALL configured recipients

### Who Receives the Emails

**Every 30 seconds, a bundled email is sent to:**
1. ✅ **Admin Email** (`frdsconnect7799@gmail.com` or configured admin)
2. ✅ **Your Recipient Email** (from User Settings)
3. ✅ **Emergency Email** (from Emergency Alert Settings)
4. ✅ **ALL Emergency Contacts** (all contacts you configured)

**Email Contents**:
- Subject: "🛑 EMERGENCY UPDATE #X - [Your Name] 🛑"
- Body: Current location, activity summary, device info
- Attachments: All captured files (camera, mic, screen, etc.)

### Database Records

**When emergency starts**, a new record is created in `emergency_alerts` table:

```
Initial Insert:
✅ user_id, device_hash, triggered_at
✅ user_name, user_email, user_phone, device_name
✅ last_location, activity_summary
✅ emergency_contacts (array)
✅ status = "new"
```

**After each email sent** (via secure RPC):
```
✅ email_sent_to_user = true
✅ email_sent_to_admin = true  
✅ email_sent_to_user_at = timestamp
✅ email_sent_to_admin_at = timestamp
✅ email_details = {recipients, subject, sender}
```

**After contacts notified** (via secure RPC):
```
✅ emergency_contacts_notified = [array of contacts]
✅ emergency_contacts_notified_count = number
```

**Every 30 seconds** (periodic updates):
```
✅ last_location = updated coordinates
✅ activity_summary = current activity
```

### How to Stop Emergency Mode

**Option 1: Dashboard Button**
- Click "🛑 EMERGENCY MODE IS ON - CLICK TO TURN OFF 🛑"
- Enter your 4-digit PIN (if configured)
- Emergency stops immediately

**Option 2: Grace Period/Control Window**
- Click "🛑 STOP EMERGENCY MODE 🛑" button
- Enter your 4-digit PIN (if configured)
- Window closes, emergency stops

**What Happens When You Stop:**
1. All data collection stops immediately
2. Final bundled email sent with any remaining data
3. Database record updated: `status = "stopped"`
4. Subscription restrictions restored
5. All features return to normal

### Duration Limits

**Default**: 59 minutes maximum
**Configurable**: Set in Emergency Alert Settings

After the time limit:
- Emergency mode stops automatically
- Final email sent
- All data saved to database

### Important Notes

✅ **No Subscription Required**: Emergency mode works for ALL users
✅ **Respects Your Preferences**: Only collects data YOU enabled
✅ **Bundled Emails**: ONE email per 30 seconds (not multiple)
✅ **Secure**: All database updates use secure RPC functions
✅ **PIN Protected**: Stopping requires PIN (if configured)
✅ **Persistent Window**: Control window stays visible until stopped

### Troubleshooting

**Grace Period Window Not Opening?**
- Check logs: `emoniter.log`
- Ensure Emergency Alert is enabled in Settings
- Ensure Data Sharing Consent is checked
- Restart the application

**Database Not Updating?**
- **CRITICAL**: Run `fix_sender_pool_rls.sql` in Supabase
- This creates secure RPC functions
- Without this, you'll see "permission denied" errors

**Can't Stop Emergency Mode?**
- Use Dashboard button OR Control window button
- Both require PIN (if configured)
- Window cannot be closed without stopping emergency first

### Security Features

🔒 **Database Security**:
- Users can ONLY update their own alerts
- Limited to specific tracking fields
- No direct table access (prevents SQL injection)
- All updates verified with ownership checks

🔒 **PIN Protection**:
- Stopping emergency requires 4-digit PIN
- Prevents accidental stops
- Configurable in Emergency Alert Settings

🔒 **Data Privacy**:
- You control what data is collected
- Only enabled features are captured
- Data sharing preferences respected

## Summary

Emergency Mode is a **life-saving feature** that:
- ✅ Bypasses ALL subscription restrictions
- ✅ Collects maximum evidence based on YOUR preferences
- ✅ Sends bundled updates every 30 seconds
- ✅ Notifies ALL your emergency contacts
- ✅ Maintains a complete database record
- ✅ Stays active until YOU stop it (or time limit)
- ✅ Requires PIN to stop (prevents tampering)

**This is designed to protect you in real emergencies.**
