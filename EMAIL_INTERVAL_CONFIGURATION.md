# Emergency Email Interval - User Configurable

## ✅ **Feature Already Implemented!**

The email update interval is **already configurable** by the user in Settings. You can set how often emergency data is sent (from 30 seconds to 5 minutes).

---

## **How to Configure Email Interval**

### In Settings UI:

1. Open eMonitor
2. Go to **Settings** → **Emergency Alert**
3. Find **"Email Update Interval"** slider
4. Adjust from **30 seconds to 5 minutes** (300 seconds)
5. Click **Save**

### Slider Options:
- **30 seconds** (minimum) - Fastest updates, more emails
- **1 minute** (60 seconds) - Balanced
- **2 minutes** (120 seconds) - Less frequent
- **5 minutes** (300 seconds) - Maximum interval

---

## **How It Works**

### Data Capture:
```
Emergency Triggered
   ↓
Continuous Capture Starts:
- Screenshots (every interval)
- Videos (continuous 30s chunks)
- Audio (continuous 30s chunks)
- Activity/Telemetry (every 15s)
   ↓
Data Buffered in Memory
```

### Email Sending (Based on Your Interval):

#### Example: 30-Second Interval
```
09:00:00 - Emergency triggered
09:00:32 - UPDATE #1 sent (with files from 0-30s)
09:01:02 - UPDATE #2 sent (with files from 30-60s)
09:01:32 - UPDATE #3 sent (with files from 60-90s)
... continues every 30 seconds ...
```

#### Example: 2-Minute Interval
```
09:00:00 - Emergency triggered
09:02:02 - UPDATE #1 sent (with files from 0-120s)
09:04:02 - UPDATE #2 sent (with files from 120-240s)
09:06:02 - UPDATE #3 sent (with files from 240-360s)
... continues every 2 minutes ...
```

---

## **Data Accumulation**

### Shorter Interval (30 seconds):
✅ **More frequent updates** - Recipients get data faster  
✅ **Smaller emails** - Each email has ~30s of data  
⚠️ **More emails** - Could fill inbox quickly  

**Example Email Size**: ~15-22 MB (30s of video/audio/screenshots)

### Longer Interval (2-5 minutes):
✅ **Fewer emails** - Less inbox clutter  
✅ **More data per email** - Comprehensive updates  
⚠️ **Larger emails** - May exceed 25MB limit  
⚠️ **Delayed updates** - Recipients wait longer  

**Example Email Size**: ~60-100 MB (2 min of data) → **May exceed Gmail limit!**

---

## **Smart File Management**

### If Email Would Exceed 20MB:
The system automatically:
1. Sorts files by size (smallest first)
2. Attaches small files first (screenshots, PDFs, audio)
3. Skips large video files if needed
4. Logs which files were skipped

**Example**:
```
User sets 5-minute interval
5 minutes of data captured:
- 10 screenshots (20 MB)
- 5 screen recordings (40 MB)
- 5 camera videos (35 MB)
- Activity PDFs (1 MB)
- Audio (25 MB)
TOTAL: 121 MB ❌ TOO LARGE!

System sends:
✅ Activity PDFs (1 MB)
✅ 10 Screenshots (20 MB)
❌ Skips videos (would exceed limit)
❌ Skips audio (would exceed limit)

Email sent: 21 MB ✅
Skipped files saved locally for manual upload
```

---

## **Recommended Settings**

### For Maximum Coverage:
- **Interval**: 30-60 seconds
- **Pros**: Fast updates, all files fit in email
- **Cons**: More emails

### For Balanced Approach:
- **Interval**: 1-2 minutes
- **Pros**: Good balance of frequency and data
- **Cons**: Some large files may be skipped

### For Minimal Emails:
- **Interval**: 3-5 minutes
- **Pros**: Fewer emails
- **Cons**: Large files will be skipped, delayed updates

---

## **Initial Email Text (Dynamic)**

The initial emergency alert email now shows your configured interval:

### If you set 30 seconds:
```
📎 DATA CAPTURE STATUS:
✓ Screenshots: Will be sent in periodic updates (every 30 seconds)
✓ Camera: Will be sent in periodic updates (every 30 seconds)
✓ Microphone: Will be sent in periodic updates (every 30 seconds)
✓ Screen Recording: Will be sent in periodic updates (every 30 seconds)
```

### If you set 2 minutes:
```
📎 DATA CAPTURE STATUS:
✓ Screenshots: Will be sent in periodic updates (every 2 minutes)
✓ Camera: Will be sent in periodic updates (every 2 minutes)
✓ Microphone: Will be sent in periodic updates (every 2 minutes)
✓ Screen Recording: Will be sent in periodic updates (every 2 minutes)
```

### If you set 90 seconds:
```
📎 DATA CAPTURE STATUS:
✓ Screenshots: Will be sent in periodic updates (every 1m 30s)
✓ Camera: Will be sent in periodic updates (every 1m 30s)
✓ Microphone: Will be sent in periodic updates (every 1m 30s)
✓ Screen Recording: Will be sent in periodic updates (every 1m 30s)
```

---

## **PDF Conversion Status**

### Why PDFs Might Not Be Sent:

1. **Conversion Error**: Check logs for:
   ```
   WARNING: EMERGENCY: Could not convert JSON to PDF: [error]
   ```

2. **File Size**: PDFs are larger than JSON (~0.2 MB vs 0.1 MB)
   - If email is near limit, PDFs might be skipped
   - Check logs for:
     ```
     WARNING: EMERGENCY: Skipped large file Activity.pdf (0.3 MB)
     ```

3. **Library Missing**: `fpdf2` not installed
   - Run: `python -m pip install fpdf2`

### To Verify PDF Conversion:

Check logs for:
```
INFO: EMERGENCY: Converted JSON files to PDF format
INFO: EMERGENCY: Attached 6 files (total ~18.5 MB)
  - jarvis - Activity - 2026-01-05_09-38-27.pdf ✅
  - jarvis - Telemetry - 2026-01-05_09-38-27.pdf ✅
```

---

## **Configuration File**

The interval is stored in `app_data/settings.json`:

```json
{
  "emergency": {
    "email_interval_seconds": 30,
    "max_duration_minutes": 59,
    "enabled": true,
    ...
  }
}
```

You can manually edit this file if needed (restart app after editing).

---

## **Summary**

✅ **Email interval is user-configurable** (30s to 5min)  
✅ **Set in Settings → Emergency Alert**  
✅ **Initial email shows your configured interval**  
✅ **Data captured continuously**  
✅ **Emails sent at your chosen interval**  
✅ **Smart file management prevents oversized emails**  
✅ **PDF conversion automatic** (if fpdf2 installed)  

**Recommended**: Start with **1 minute** interval for best balance!
