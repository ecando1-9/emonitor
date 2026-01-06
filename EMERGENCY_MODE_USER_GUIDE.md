# Emergency Mode - Quick Reference Guide

## What Gets Captured During Emergency?

The emergency mode will **ONLY** capture data that you have enabled in your settings. Here's how it works:

### Settings Page → Emergency Alert Data Sharing Preferences

When you configure emergency mode in Settings, you can choose exactly what data to share:

| Setting | What It Does | Captured If Enabled |
|---------|-------------|---------------------|
| **Screenshot** | Takes a screenshot of your screen | ✅ One screenshot |
| **Screen Record** | Records your screen for 30 seconds | ✅ 30-second video |
| **Camera** | Records from webcam with audio | ✅ 30-second video (if camera connected) |
| **Microphone** | Records audio from microphone | ✅ 30-second audio (if mic connected) |
| **Device Info** | Shares device name and specs | ✅ Device details |
| **Last Location** | Shares your GPS location | ✅ Location data |
| **Activity Summary** | Shares what apps you're using | ✅ Active window info |
| **Typing Intensity** | Records keyboard activity | ✅ 10 minutes of typing data |
| **Logs** | Shares system logs | ✅ Log files |

### Important Notes:

1. **User Control**: You decide what to share. Unchecked items will NOT be captured.

2. **Device Availability**: 
   - If camera is not connected → Skips camera, continues with other captures
   - If microphone is not connected → Skips microphone, continues with other captures
   - **Emergency mode will NOT fail** if a device is unavailable

3. **Unencrypted Data**: During emergency, all files are sent **without encryption** for immediate admin access.

---

## How Emergency Mode Works

### 1. Activation
- Double-click the desktop shortcut
- Enter your emergency PIN
- Emergency mode starts **immediately**

### 2. Data Collection (Based on Your Settings)
```
✅ Enabled features start capturing
⏭️ Disabled features are skipped
⚠️ Unavailable devices show warning but don't stop the process
```

### 3. Data Transmission
- Updates sent every **30 seconds**
- Sent to:
  - Your recipient email
  - Your emergency email
  - Admin support email (for monitoring)
- Continues for **30 minutes** or until you stop it

### 4. Stopping Emergency Mode
- Click **"Stop Emergency"** button in dashboard
- Emergency mode stops **immediately**
- Final update sent to all recipients
- All data collection stops

---

## Example Scenarios

### Scenario 1: Camera Not Connected
```
User Settings:
✅ Camera enabled
✅ Screen Record enabled
✅ Activity Summary enabled

What Happens:
✅ Screen recording starts (30 sec)
✅ Activity captured
⚠️ Camera skipped (not connected) - WARNING logged
✅ Emergency continues normally
```

### Scenario 2: User Wants Minimal Data Sharing
```
User Settings:
❌ Camera disabled
❌ Screen Record disabled
✅ Activity Summary enabled
✅ Last Location enabled

What Happens:
⏭️ Camera skipped (user preference)
⏭️ Screen record skipped (user preference)
✅ Activity captured
✅ Location captured
✅ Emergency continues with only enabled features
```

### Scenario 3: Full Emergency Mode
```
User Settings:
✅ All features enabled
✅ Camera connected
✅ Microphone connected

What Happens:
✅ Screen recording (30 sec)
✅ Camera recording (30 sec with audio)
✅ Microphone recording (30 sec)
✅ Activity captured
✅ Location captured
✅ Telemetry captured
✅ Typed activity (10 min)
✅ All data sent every 30 seconds
```

---

## Troubleshooting

### "Camera not working during emergency"
- **Check**: Is camera physically connected?
- **Check**: Is camera being used by another app?
- **Result**: Emergency mode continues without camera

### "Microphone not working during emergency"
- **Check**: Is microphone physically connected?
- **Check**: Is microphone being used by another app?
- **Result**: Emergency mode continues without microphone

### "Not receiving emergency emails"
- **Check**: Is SMTP configured in settings?
- **Check**: Run `fix_sender_pool_rls.sql` in Supabase
- **Check**: Check spam folder

### "Emergency mode won't stop"
- **Solution**: Click "Stop Emergency" button in dashboard
- **Fallback**: Restart the application

---

## Privacy & Security

### What You Control:
✅ Which data types to share (via checkboxes)  
✅ Who receives the data (emergency contacts)  
✅ When to trigger emergency mode (PIN protected)  
✅ When to stop emergency mode (immediate stop button)  

### What Happens to Your Data:
- Stored in **Supabase database** (encrypted at rest)
- Sent to **your designated recipients** only
- **Admin access** for emergency response support
- **No encryption** during emergency for faster access

### Data Retention:
- Emergency alerts stored in database
- Can be reviewed by admins for emergency response
- User can request deletion after emergency is resolved

---

## Best Practices

1. **Test Emergency Mode** before you need it
   - Trigger it once to see what gets captured
   - Check if emails are received
   - Verify camera/microphone work

2. **Configure Settings Carefully**
   - Only enable data you're comfortable sharing
   - Add trusted emergency contacts
   - Set a memorable but secure PIN

3. **Keep Devices Ready**
   - Ensure camera is connected if enabled
   - Ensure microphone is connected if enabled
   - Keep laptop charged

4. **Update Emergency Contacts**
   - Review contacts periodically
   - Remove outdated contacts
   - Add new trusted contacts

---

## Support

If you encounter issues with emergency mode:

1. Check the logs for error messages (look for ❌ symbols)
2. Verify your settings in Settings → Emergency Alert Settings
3. Run the database fix script if seeing permission errors
4. Contact support with log details

---

**Remember**: Emergency mode is designed to work even if some features fail. It will capture and send whatever data is available based on your settings and device availability.
