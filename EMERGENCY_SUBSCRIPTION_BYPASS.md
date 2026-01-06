# Emergency Mode - Subscription Bypass Requirements

## Critical Requirement
**Emergency mode MUST work regardless of user subscription status and send all captured data to destination emails.**

## What Needs to Be Ensured

### 1. Emergency Mode Activation
- ✅ `enable_all_features_for_emergency()` already bypasses subscription by enabling ALL features
- ✅ Emergency mode should activate regardless of subscription status
- ✅ All capture features (camera, microphone, screen record, etc.) should work in emergency mode

### 2. File Sending Logic
The `process_emergency_file_unencrypted()` function MUST:
- ✅ Send files to **recipient email** (settings.user.recipient_email)
- ✅ Send files to **emergency email** (settings.emergency.emergency_email)
- ❌ **DO NOT** send to admin email
- ✅ **Bypass all subscription checks** - emergency files should always be sent
- ✅ Use `send_instant_report()` from sender.py to send files directly

### 3. Email Sending Logic
The `send_emergency_email()` function MUST:
- ✅ Send to **recipient email** only
- ✅ Send to **emergency email** only
- ❌ **DO NOT** send to admin email
- ✅ **Bypass subscription checks** - always send emergency emails

### 4. Periodic Updates
The `send_emergency_data_periodically()` function MUST:
- ✅ Send updates to **recipient email** every 30 seconds
- ✅ Send updates to **emergency email** every 30 seconds
- ❌ **DO NOT** send to admin email
- ✅ **Bypass subscription checks**

## Implementation Notes

### Current Status
- `enable_all_features_for_emergency()` - ✅ Already bypasses subscription
- Emergency mode activation - ✅ Works regardless of subscription
- File sending - ⚠️ Need to verify `process_emergency_file_unencrypted()` bypasses subscription
- Email sending - ⚠️ Need to verify no subscription checks in email functions

### Required Changes
1. Ensure `process_emergency_file_unencrypted()` sends to recipient + emergency email only
2. Ensure `send_emergency_email()` sends to recipient + emergency email only (NOT admin)
3. Remove any subscription checks from emergency file/email sending logic
4. Ensure emergency files are sent via `send_instant_report()` which should work regardless of subscription

## Testing Checklist
- [ ] Emergency mode activates with expired subscription
- [ ] Emergency mode activates with no subscription
- [ ] Camera capture works in emergency mode (regardless of subscription)
- [ ] Microphone capture works in emergency mode (regardless of subscription)
- [ ] Captured files are sent to recipient email
- [ ] Captured files are sent to emergency email
- [ ] Captured files are NOT sent to admin email
- [ ] Periodic email updates are sent to recipient + emergency email only

