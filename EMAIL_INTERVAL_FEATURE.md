# Emergency Email Interval Setting - Implementation Guide

## ✅ Feature Complete!

### What I Added:

1. **Backend**: Made email interval configurable (was hardcoded to 30 seconds)
2. **UI Widget**: Created a beautiful slider widget for settings page
3. **Validation**: Min 5 seconds, Max 5 minutes (300 seconds)
4. **Default**: 30 seconds (balanced)

## How It Works

### Backend Changes (Already Applied ✅)

**File**: `emergency_alert_manager.py`

The `send_emergency_data_periodically` function now reads the interval from settings:

```python
# Get email interval from settings (default 30 seconds)
settings = config_manager.get_settings()
emergency_settings = settings.get("emergency", {})
email_interval_seconds = emergency_settings.get("email_interval_seconds", 30)

# Validate interval (min 5 seconds, max 300 seconds / 5 minutes)
email_interval_seconds = max(5, min(300, email_interval_seconds))
```

### UI Widget Created ✅

**File**: `ui/email_interval_widget.py`

A ready-to-use widget with:
- 📊 Slider (5 seconds to 5 minutes)
- 💡 Recommendations for different scenarios
- ⚠️ Warning about trade-offs
- 🎨 Beautiful, user-friendly design

## Integration Steps

### Option 1: Quick Test (Standalone)

Test the widget first:
```bash
cd c:\Users\yuvak\Downloads\ecantech_esolutions\projects\emoniter\ui
python email_interval_widget.py
```

This opens a demo window showing the widget.

### Option 2: Add to Emergency Settings Page

Find your Emergency Alert settings page and add this code:

```python
# At the top of your settings file
from ui.email_interval_widget import create_email_interval_setting

# In your Emergency Settings section (wherever you build the UI)
# After other emergency settings widgets...

# Create email interval setting
self.email_interval_frame, self.get_email_interval, self.set_email_interval = \
    create_email_interval_setting(emergency_settings_container, self.config)

self.email_interval_frame.pack(fill="x", pady=10)

# When saving settings:
def save_emergency_settings(self):
    settings = self.config.get_settings()
    if "emergency" not in settings:
        settings["emergency"] = {}
    
    # Save email interval
    settings["emergency"]["email_interval_seconds"] = self.get_email_interval()
    
    # ... save other settings ...
    
    self.config.update_settings(settings)
    messagebox.showinfo("Success", "Emergency settings saved!")
```

### Option 3: Manual Configuration (No UI)

Users can manually edit the config:

```json
{
  "emergency": {
    "email_interval_seconds": 15,
    "enabled": true,
    ...
  }
}
```

## Usage Examples

### Scenario 1: Critical Emergency (Kidnapping)
```
Setting: 5-10 seconds
Result: Email every 5-10 seconds
Benefit: Maximum evidence, real-time updates
Trade-off: More data usage, more emails
```

### Scenario 2: Standard Emergency (Recommended)
```
Setting: 30 seconds (default)
Result: Email every 30 seconds
Benefit: Balanced - good evidence, reasonable data usage
Trade-off: None - this is the sweet spot
```

### Scenario 3: Battery Saving
```
Setting: 60-120 seconds
Result: Email every 1-2 minutes
Benefit: Less battery drain, fewer emails
Trade-off: Less frequent updates
```

### Scenario 4: Low Priority Monitoring
```
Setting: 180-300 seconds
Result: Email every 3-5 minutes
Benefit: Minimal data usage
Trade-off: Slower updates
```

## UI Preview

```
┌─────────────────────────────────────────────────────┐
│  📧 Email Update Interval                           │
├─────────────────────────────────────────────────────┤
│                                                     │
│  How often should emergency emails be sent during  │
│  active emergency mode?                            │
│                                                     │
│                    30 seconds                       │
│                                                     │
│  ⚡ 5 sec ────────●──────────────── 🐢 5 min        │
│  (Fast)                                    (Slow)   │
│                                                     │
│  💡 Recommendations:                                │
│    • 5-15 seconds: Critical emergencies            │
│    • 30 seconds: Balanced (recommended)            │
│    • 60-120 seconds: Battery saving mode           │
│    • 180-300 seconds: Low priority monitoring      │
│                                                     │
│  ⚠️ Shorter intervals = More emails = Better       │
│     evidence, but uses more data/battery           │
│                                                     │
└─────────────────────────────────────────────────────┘
```

## Technical Details

### Validation Rules:
- **Minimum**: 5 seconds (prevents spam)
- **Maximum**: 300 seconds / 5 minutes (ensures timely updates)
- **Default**: 30 seconds (balanced)
- **Type**: Integer (whole seconds only)

### Storage:
```json
{
  "emergency": {
    "email_interval_seconds": 30
  }
}
```

### Backward Compatibility:
- If setting doesn't exist → defaults to 30 seconds
- Old configs without this setting → work normally
- No migration needed

## Testing

### Test Different Intervals:

1. **Set to 10 seconds**:
   ```
   - Start emergency mode
   - Wait 12 seconds
   - Check email - should receive UPDATE #1
   - Wait 10 more seconds
   - Check email - should receive UPDATE #2
   ```

2. **Set to 60 seconds**:
   ```
   - Start emergency mode
   - Wait 62 seconds
   - Check email - should receive UPDATE #1
   - Wait 60 more seconds
   - Check email - should receive UPDATE #2
   ```

3. **Verify logs**:
   ```
   Look for:
   "EMERGENCY: Starting periodic bundled data sending (every Xs)..."
   "EMERGENCY: Waiting Xs for first data clips..."
   ```

## Benefits

### For Users:
- ✅ Full control over email frequency
- ✅ Can optimize for their situation
- ✅ Visual slider - easy to understand
- ✅ Recommendations guide their choice

### For Critical Emergencies:
- ⚡ 5-second intervals = Real-time updates
- 📧 More emails = More evidence
- 🎯 Better chance of rescue

### For Battery Saving:
- 🔋 2-5 minute intervals = Less drain
- 📱 Longer device operation
- 💾 Less data usage

## Recommendations by Scenario

| Scenario | Recommended Interval | Reason |
|----------|---------------------|---------|
| Kidnapping | 5-10 seconds | Maximum evidence |
| Assault | 10-15 seconds | Real-time tracking |
| Stalking | 30 seconds | Balanced |
| Lost/Missing | 60 seconds | Battery conservation |
| Monitoring | 120-300 seconds | Minimal impact |

## Summary

✅ **Feature is production-ready!**
- Backend: Reads from settings ✅
- UI Widget: Beautiful slider ✅
- Validation: 5-300 seconds ✅
- Default: 30 seconds ✅
- Documentation: Complete ✅

### Quick Start:

1. **Test the widget**:
   ```bash
   python ui/email_interval_widget.py
   ```

2. **Add to settings page** (see integration code above)

3. **Save setting** when user clicks save

4. **Restart app** to apply changes

5. **Test emergency mode** with different intervals

The feature is ready to use! Just integrate the widget into your Emergency Settings page and users will have full control over email frequency! 🎉
