# Emergency Mode - Quick Reference Guide

## ✅ WHAT'S BEEN FIXED

### 1. Grace Period Window
- **Issue**: Window was auto-closing after countdown
- **Fix**: Removed auto-close logic, window stays open until user clicks button
- **Result**: User has time to review and manually close the window

### 2. Cancel Option
- **Issue**: No visible cancel button during grace period
- **Fix**: Red "✕ CANCEL ALERT" button shown during entire countdown
- **Result**: User can click CANCEL anytime during 15-second grace period

### 3. User Details Storage
- **Issue**: User name, phone, device info not stored in database
- **Fix**: All user details now saved to emergency_alerts table:
  - `user_name` - From settings
  - `user_phone` - From settings  
  - `user_email` - From settings
  - `device_name` - From settings
  - `device_hash` - Device fingerprint
  - `emergency_contacts` - Contact list (JSONB array)
- **Result**: Complete user info available in database for admin

### 4. Button State Updates
- **Issue**: Dashboard button not updating immediately after trigger
- **Fix**: Added immediate state refresh with `self.after(100, self.update_emergency_button_state)`
- **Result**: Button changes to OFF/Cancel state immediately

### 5. Periodic Email Sending
- **Issue**: Only sending on final stop
- **Fix**: Now sends every 30 seconds to:
  - Admin email
  - User email
  - User emergency email (if configured)
  - System emergency email
- **Result**: Real-time data updates every 30 seconds

## 🚀 HOW TO USE

### Start Emergency Mode
1. Open app: `python main.py`
2. Login with credentials
3. Click "🚨 TURN ON EMERGENCY 🚨" on Dashboard
4. **15-second grace period** appears with:
   - Countdown timer
   - Red "✕ CANCEL ALERT" button
5. Let countdown finish OR click CANCEL to stop

### After Grace Period (Alert Sent)
1. Button changes to green "✓ CLOSE WINDOW"
2. Emergency mode becomes **ACTIVE**
3. Dashboard shows "Emergency Mode: ON" (red)
4. Data collection starts immediately
5. Emails sent every 30 seconds

### Stop Emergency Mode
1. Click "🛑 TURN OFF EMERGENCY 🛑" on Dashboard
2. Confirmation dialog appears
3. Click YES to stop
4. "✓ Emergency Stopped" message shows
5. Dashboard returns to "Emergency Mode: OFF" (green)

## 📧 EMAIL CONFIGURATION

### Emails Receive Updates Every 30 Seconds When Emergency is ON:

**1. Admin Email**
- Path: Settings → Admin Email
- Contains: Location, activity, device info, contacts

**2. User Email**
- Path: Settings → User Email
- Contains: Same as admin + user details

**3. User Emergency Email**
- Path: Settings → Emergency → Emergency Email
- Contains: Full emergency data
- Optional - leave blank if not needed

**4. System Emergency Email**
- Email: `ecando976@gmail.com` (hardcoded)
- Always receives updates when emergency is ON

### Configure Emails
1. Go to Settings
2. Set "Admin Email" under Admin section
3. Set "Recipient Email" under User section
4. Set "Emergency Email" under Emergency section (optional)
5. Ensure SMTP credentials configured in Admin Panel

## 🗄️ DATABASE FIELDS UPDATED

Emergency alerts now store:
```
{
  user_id: UUID from authentication
  user_name: String from settings.emergency.user_name
  user_email: String from settings.user.recipient_email
  user_phone: String from settings.emergency.user_phone
  device_name: String from settings.user.device_name
  device_hash: String device fingerprint
  emergency_contacts: JSON array [{name, phone, email, relationship}]
  last_location: JSON {latitude, longitude, accuracy}
  activity_summary: String (recent activity)
  status: String ("new", "active", "stopped")
  triggered_at: Timestamp
  email_sent_to_user: Boolean
  email_sent_to_admin: Boolean
  email_details: JSON tracking
  ... and more
}
```

## ✓ CHECKLIST BEFORE USING

- [ ] Emergency feature enabled in Settings
- [ ] Data sharing consent given
- [ ] User name filled in Emergency settings
- [ ] User phone filled in Emergency settings (optional)
- [ ] Admin email configured
- [ ] User email configured
- [ ] User emergency email configured (optional)
- [ ] SMTP credentials added via Admin Panel or settings.json
- [ ] At least 1 emergency contact added
- [ ] Desktop shortcut PIN set (if using desktop trigger)

## 🧪 TEST FLOW

```
1. Start app
   python main.py

2. Go to Dashboard
   Should see: "Emergency Mode: OFF" (green)
             "🚨 TURN ON EMERGENCY 🚨" button

3. Click TURN ON
   Grace period window appears
   Countdown: 15 seconds
   Red CANCEL button visible

4. Wait OR click CANCEL
   If wait: Alert sent → button changes to "TURN OFF"
   If cancel: Returns to Dashboard

5. Click TURN OFF
   Confirmation dialog
   Shows "Emergency Stopped" message
   Returns to OFF state

6. Check email
   Should have 4 emails with latest data
```

## 🐛 TROUBLESHOOTING

**No emails received?**
- Check SMTP credentials in Admin Panel
- Verify admin email configured
- Check firewall/network blocking SMTP

**Grace period window closing too fast?**
- Already fixed! Window stays open now
- Click "CLOSE WINDOW" button to close manually

**User details not saving?**
- Settings must be filled before triggering emergency
- Fill all fields in Settings → Emergency

**Desktop shortcut not working?**
- Ensure PIN is set in Settings
- Desktop shortcut creates shortcut on desktop
- Right-click desktop shortcut to trigger with PIN

**Database not updating?**
- Check Supabase connection
- Verify user is logged in
- Check logs for database errors

## 📝 LOGS LOCATION

Check logs at: `emoniter.log`

Look for:
- "EMERGENCY ALERT TRIGGERED"
- "Periodic data sending"
- "Sent update to" (for email sends)
- "Successfully created emergency alert"

## 🎯 FEATURES

✅ Emergency ON/OFF toggle
✅ 15-second grace period with cancel option
✅ User details stored in database
✅ Data collection (screenshots, activity, location)
✅ Periodic email every 30 seconds
✅ Multiple email recipients
✅ Emergency status display on dashboard
✅ Desktop shortcut trigger (with PIN)
✅ Emergency contact notifications
✅ Error message sanitization
✅ Geometry manager consistency (pack)
✅ 30-minute maximum duration

---
**Last Updated**: December 6, 2025
**Version**: 2.0 (Complete with all fixes)
