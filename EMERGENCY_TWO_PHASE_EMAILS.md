# Emergency Email System - Two-Phase Delivery

## ⚠️ IMPORTANT: Why You Didn't Receive Files

The emergency system sends emails in **TWO PHASES**:

### Phase 1: INITIAL ALERT (Immediate)
**What you received at 9:34 AM**

This is sent **immediately** when emergency is triggered:
- ✅ User information
- ✅ Device information  
- ✅ Location data
- ✅ Recent activity
- ❌ **NO FILE ATTACHMENTS**

**Purpose**: Notify recipients ASAP that an emergency has occurred

**Email Subject**: "EMERGENCY ALERT - Immediate Action Required"

**Why no files?**
- Sent instantly (no time to capture media)
- Just alerts you that emergency mode is active
- Files come in Phase 2

---

### Phase 2: PERIODIC UPDATES (Every 30 Seconds)
**What you should receive starting 30 seconds after trigger**

These emails contain **ACTUAL FILE ATTACHMENTS**:
- 📸 Screenshots (`.png`)
- 🎥 Screen recordings (`.mp4`)
- 📹 Camera videos (`.mp4`)
- 🎤 Microphone audio (`.wav`)
- 📊 Activity logs (`.json`)
- 📍 Telemetry data (`.json`)

**Email Subject**: "🛑 EMERGENCY UPDATE #1 - tony 🛑"

**Frequency**: Every 30 seconds until emergency is stopped

**Recipients**:
- `ecando976@gmail.com` (admin)
- Your emergency email
- Emergency contacts

---

## 📧 What The NEW Initial Email Will Say

After the fix, the initial alert will clearly state:

```
EMERGENCY ALERT - IMMEDIATE ACTION REQUIRED

User: tony
Email: yuva7@gmail.com
Timestamp: 2026-01-05T09:34:07

Device Information:
- Device Name: jarvis
- Device ID: 11e55f5eb20...

Location Information:
{
  "latitude": 17.5783,
  "longitude": 78.5887,
  "accuracy_meters": 50000.0
}

Recent Activity:
eMonitor

📎 DATA CAPTURE STATUS:
✓ Screenshots: Will be sent in periodic updates (every 30 sec)
✓ Camera: Will be sent in periodic updates (every 30 sec)
✓ Microphone: Will be sent in periodic updates (every 30 sec)
✓ Screen Recording: Will be sent in periodic updates (every 30 sec)

--- Emergency Contact Notification ---
This is an automated emergency notification.
Please contact the user or emergency services if needed.
```

**Key Change**: Now says "Will be sent in periodic updates" instead of "is attached"

---

## 📧 What The Periodic Update Emails Look Like

**Subject**: 🛑 EMERGENCY UPDATE #1 - tony 🛑

**Body**:
```
EMERGENCY ALERT - UPDATE #1
Time: 2026-01-05T09:34:37+05:30
Device: jarvis
User: tony
Status: ACTIVE

--- LOCATION DATA ---
{
  "latitude": 17.5783,
  "longitude": 78.5887
}

--- RECENT ACTIVITY ---
eMonitor - Dashboard

--- ATTACHED DATA CLIPS (5 files) ---
- jarvis - Screenshot - 2026-01-05_09-34-30.png
- jarvis - Camera - 2026-01-05_09-34-35.mp4
- jarvis - Activity - 2026-01-05_09-34-36.json
- jarvis - Telemetry - 2026-01-05_09-34-37.json
- jarvis - Microphone - 2026-01-05_09-34-38.wav

---
PROTECTIVE MONITORING ACTIVE.
This is an automated emergency update from eMonitor.
```

**Attachments**: 5 files (screenshots, videos, audio, data)

---

## ⏱️ Timeline Example

```
09:34:00 - Emergency triggered
09:34:07 - INITIAL ALERT sent (no files)
           ↓
09:34:30 - First 30-second window completes
           - Screenshot captured
           - Camera video captured
           - Microphone audio captured
           - Activity/telemetry logged
           ↓
09:34:37 - UPDATE #1 sent (WITH 5 FILES ATTACHED)
           ↓
09:35:00 - Second 30-second window completes
           - More files captured
           ↓
09:35:07 - UPDATE #2 sent (WITH NEW FILES)
           ↓
... continues every 30 seconds ...
           ↓
09:40:00 - User stops emergency
           ↓
09:40:05 - FINAL UPDATE sent (STOPPED status)
```

---

## ✅ How To Verify Files Are Being Sent

### Check Your Email Inbox:

1. **First Email** (9:34 AM):
   - Subject: "EMERGENCY ALERT - Immediate Action Required"
   - ❌ No attachments (this is normal!)
   - ✅ Says "Will be sent in periodic updates"

2. **Second Email** (9:34:30 AM or later):
   - Subject: "🛑 EMERGENCY UPDATE #1 - tony 🛑"
   - ✅ HAS ATTACHMENTS (screenshots, videos, audio)
   - Lists files in email body

3. **Third Email** (9:35:00 AM):
   - Subject: "🛑 EMERGENCY UPDATE #2 - tony 🛑"
   - ✅ HAS NEW ATTACHMENTS
   - Fresh files from second 30-second window

### If You're NOT Receiving Update Emails:

**Possible Reasons**:
1. Emergency was stopped before 30 seconds elapsed
2. SMTP sender credentials issue
3. Email going to spam folder
4. Features not enabled in Emergency Settings

**Check Logs For**:
```
INFO: EMERGENCY: Sent UPDATE #1 to ecando976@gmail.com
INFO: EMERGENCY: Sent UPDATE #1 to frdsconnect7799@gmail.com
```

If you see these logs, emails were sent successfully!

---

## 🔧 What Was Fixed

**Before**:
- Initial email said "Screenshot has been taken and is attached"
- User expected files but didn't receive them
- Confusing and misleading

**After**:
- Initial email says "Screenshots: Will be sent in periodic updates (every 30 sec)"
- Clear expectation that files come later
- No confusion

---

## 📝 Summary

- ✅ **Initial Alert**: Sent immediately, NO files (just notification)
- ✅ **Periodic Updates**: Sent every 30 seconds, WITH files attached
- ✅ **Recipients**: Admin + your emergency email + emergency contacts
- ✅ **Files**: Screenshots, videos, audio, activity logs
- ✅ **Cleanup**: Files deleted after sending (saves space)

**The system is working correctly!** You just need to wait 30 seconds for the first file-attached email.
