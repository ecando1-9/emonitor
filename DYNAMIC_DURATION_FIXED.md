# ✅ Duration Now Fully Dynamic from Settings!

## What I Fixed:

Changed emergency mode duration from **hardcoded 59 minutes** to **fully dynamic from settings page**.

### Before (Hardcoded):
```python
def send_emergency_data_periodically(alert_id, duration_minutes=59):  # ❌ Hardcoded!
    ...

def run_emergency_capture_protocol(duration_minutes=59):  # ❌ Hardcoded!
    ...
```

### After (Dynamic):
```python
def send_emergency_data_periodically(alert_id, duration_minutes=None):
    # Get duration from settings if not provided
    if duration_minutes is None:
        settings = config_manager.get_settings()
        emergency_settings = settings.get("emergency", {})
        duration_minutes = emergency_settings.get("max_duration_minutes", 59)  # ✅ From settings!
    ...

def run_emergency_capture_protocol(duration_minutes=None):
    # Get duration from settings if not provided
    if duration_minutes is None:
        settings = config_manager.get_settings()
        emergency_settings = settings.get("emergency", {})
        duration_minutes = emergency_settings.get("max_duration_minutes", 59)  # ✅ From settings!
    ...
```

## How It Works Now:

### 1. User Sets Duration in Settings
```
Settings → Emergency Alert Settings
Emergency Mode Duration: [2] [hours ▼]
                         ↑      ↑
                      Value   Unit
```

### 2. Settings Saved
```json
{
  "emergency": {
    "max_duration_minutes": 120,  // 2 hours = 120 minutes
    "duration_unit": "hours"
  }
}
```

### 3. Emergency Mode Uses Settings
```python
# When emergency starts:
duration = settings["emergency"]["max_duration_minutes"]  # 120 minutes
# Emergency will run for 120 minutes (2 hours)
```

## Examples:

### Example 1: User Sets 30 Minutes
```
Settings: 30 minutes
Saved as: max_duration_minutes = 30
Emergency runs for: 30 minutes
Stops at: 30 minutes automatically
```

### Example 2: User Sets 2 Hours
```
Settings: 2 hours
Saved as: max_duration_minutes = 120 (2 * 60)
Emergency runs for: 120 minutes (2 hours)
Stops at: 2 hours automatically
```

### Example 3: User Sets 10 Hours
```
Settings: 10 hours
Saved as: max_duration_minutes = 600 (10 * 60)
Emergency runs for: 600 minutes (10 hours)
Stops at: 10 hours automatically
```

## Logs You'll See:

### User Sets 2 Hours:
```
INFO: EMERGENCY CAPTURE PROTOCOL: Starting continuous data collection (max 120 minutes)...
INFO: EMERGENCY: Starting periodic bundled data sending (every 30s, max 120 min)...
...
WARNING: EMERGENCY: Maximum duration (120 minutes) reached. Stopping emergency mode automatically...
```

### User Sets 30 Minutes:
```
INFO: EMERGENCY CAPTURE PROTOCOL: Starting continuous data collection (max 30 minutes)...
INFO: EMERGENCY: Starting periodic bundled data sending (every 30s, max 30 min)...
...
WARNING: EMERGENCY: Maximum duration (30 minutes) reached. Stopping emergency mode automatically...
```

## Settings Page UI:

```
┌─────────────────────────────────────────────────────┐
│  Emergency Mode Duration                            │
│  (if not stopped manually)                          │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Duration: [59] ▼    Unit: [minutes ▼]             │
│                                                     │
│  Emergency mode will automatically stop after this  │
│  duration if not manually stopped. Default: 59 min. │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### Options:
- **Duration**: Any positive number (1, 2, 5, 10, 30, 59, 100, etc.)
- **Unit**: 
  - `minutes` → saved as-is
  - `hours` → multiplied by 60

## Testing:

### Test 1: Set to 2 Minutes
```
1. Settings → Emergency Alert Settings
2. Duration: 2, Unit: minutes
3. Save Settings
4. Trigger emergency
5. Wait 2 minutes
6. ✅ Stops automatically after 2 minutes
```

### Test 2: Set to 1 Hour
```
1. Settings → Emergency Alert Settings
2. Duration: 1, Unit: hours
3. Save Settings
4. Trigger emergency
5. Check logs: "max 60 minutes"
6. ✅ Will stop after 60 minutes
```

### Test 3: Change While Running (Won't Affect Current)
```
1. Start emergency with 59 minutes
2. Change settings to 30 minutes
3. Current emergency: Still runs for 59 minutes (original)
4. Next emergency: Will use 30 minutes (new setting)
```

## Summary:

✅ **Duration is now fully dynamic!**
- Reads from `settings["emergency"]["max_duration_minutes"]`
- No hardcoded 59 minutes
- User can set any duration (minutes or hours)
- Automatic stop after configured time
- No PIN required for automatic stop

### Default Behavior:
- If user never changes settings: **59 minutes** (default)
- If user sets custom duration: **Uses their setting**
- If setting is missing: **Falls back to 59 minutes**

**The feature is production-ready!** 🎉
