# Emergency Mode Testing Checklist

## Pre-Test Setup

### 1. Verify SQL Script Applied
- [ ] Opened Supabase Dashboard
- [ ] Ran `fix_sender_pool_rls.sql` in SQL Editor
- [ ] Saw "Success. No rows returned"
- [ ] Verified functions created:
  ```sql
  SELECT routine_name 
  FROM information_schema.routines 
  WHERE routine_schema = 'public' 
  AND routine_name LIKE '%emergency%';
  ```

### 2. Verify Settings Configured
- [ ] Emergency Alert enabled in Settings
- [ ] Data Sharing Consent checked
- [ ] Emergency contacts added (with emails)
- [ ] Emergency email configured
- [ ] Admin email configured
- [ ] Recipient email configured

### 3. Prepare Test Environment
- [ ] Open several applications (Chrome, Notepad, etc.)
- [ ] Have email inboxes ready to check
- [ ] Clear old log file or note current position

## Test Procedure

### Test 1: Grace Period Window
1. Click "🚨 TURN ON EMERGENCY 🚨" button
2. **Expected**: Grace period window opens
3. **Verify**: 
   - [ ] Window shows countdown (5 seconds default)
   - [ ] "CANCEL ALERT" button visible
   - [ ] Window stays on top

### Test 2: Emergency Activation
1. Wait for countdown to finish (or let it complete)
2. **Expected**: Emergency mode activates
3. **Verify**:
   - [ ] Grace window shows "✓ EMERGENCY MODE IS NOW ACTIVE ✓"
   - [ ] Button changes to "🛑 STOP EMERGENCY MODE 🛑"
   - [ ] Dashboard button shows "EMERGENCY MODE IS ON"
   - [ ] Log shows: "EMERGENCY: Starting continuous emergency capture protocol"

### Test 3: Data Collection (Wait 35 seconds)
1. Wait for first 30-second cycle to complete
2. **Expected**: Data captured and sent
3. **Verify in Logs**:
   - [ ] "EMERGENCY: Buffered screen_record chunk"
   - [ ] "EMERGENCY: Buffered camera chunk"
   - [ ] "EMERGENCY: Buffered microphone chunk"
   - [ ] "EMERGENCY: Sent UPDATE #1 to [email1]"
   - [ ] "EMERGENCY: Sent UPDATE #1 to [email2]"
   - [ ] "EMERGENCY: Sent UPDATE #1 to [email3]"

### Test 4: Email Verification
Check ALL configured email inboxes:
- [ ] **Admin Email**: Received bundled email
- [ ] **Recipient Email**: Received bundled email
- [ ] **Emergency Email**: Received bundled email
- [ ] **Contact 1 Email**: Received bundled email
- [ ] **Contact 2 Email**: Received bundled email

**Verify Email Contents**:
- [ ] Subject: "🛑 EMERGENCY UPDATE #1 - [Your Name] 🛑"
- [ ] Body contains location data
- [ ] Body contains activity summary with running apps
- [ ] Body lists attached files
- [ ] Attachments present (screen, camera, mic, telemetry, activity)

### Test 5: Database Updates
Check Supabase `emergency_alerts` table:
```sql
SELECT * FROM emergency_alerts 
ORDER BY created_at DESC 
LIMIT 1;
```

**Verify Fields**:
- [ ] `user_name` populated
- [ ] `user_email` populated
- [ ] `user_phone` populated
- [ ] `device_name` populated
- [ ] `last_location` has GPS data
- [ ] `activity_summary` has text
- [ ] `emergency_contacts` is array
- [ ] `email_sent_to_user` = true
- [ ] `email_sent_to_admin` = true
- [ ] `email_sent_to_user_at` has timestamp
- [ ] `email_sent_to_admin_at` has timestamp
- [ ] `emergency_contacts_notified` has array of contacts
- [ ] `emergency_contacts_notified_count` > 0

### Test 6: Continuous Operation (Wait 2 minutes)
1. Let emergency mode run for 2 minutes
2. **Expected**: Updates every 30 seconds
3. **Verify**:
   - [ ] Log shows "UPDATE #2" after 60 seconds
   - [ ] Log shows "UPDATE #3" after 90 seconds
   - [ ] Log shows "UPDATE #4" after 120 seconds
   - [ ] All emails received for each update
   - [ ] No crashes or errors

### Test 7: Stop Emergency Mode
1. Click "🛑 STOP EMERGENCY MODE 🛑" button
2. Enter PIN (if configured)
3. **Expected**: Emergency stops
4. **Verify**:
   - [ ] PIN prompt appears (if configured)
   - [ ] After correct PIN, emergency stops
   - [ ] Log shows "EMERGENCY: User requested to stop"
   - [ ] Log shows "EMERGENCY: Sending final bundled data update"
   - [ ] Log shows "EMERGENCY: Sent STOPPED to [emails]"
   - [ ] Dashboard button returns to "TURN ON EMERGENCY"
   - [ ] Grace window closes

### Test 8: Final Email
Check email inboxes for final email:
- [ ] Subject: "🛑 EMERGENCY STOPPED - [Your Name] 🛑"
- [ ] Body shows Status: STOPPED BY USER
- [ ] Contains any remaining data clips
- [ ] All recipients received it

### Test 9: Restart Capability
1. Wait 10 seconds
2. Click "TURN ON EMERGENCY" again
3. **Expected**: Can restart emergency mode
4. **Verify**:
   - [ ] Grace period window opens again
   - [ ] No errors about "already active"
   - [ ] New emergency session starts
   - [ ] New alert ID created in database

## Common Issues & Solutions

### Issue: "Permission denied for table emergency_alerts"
**Solution**: SQL script not applied. Run `fix_sender_pool_rls.sql` in Supabase.

### Issue: Grace period window doesn't open
**Solution**: 
- Check logs for errors
- Verify emergency alert enabled in settings
- Verify data sharing consent checked
- Restart application

### Issue: No emails received
**Solution**:
- Check SMTP credentials in `sender_pool` table
- Check spam folders
- Verify email addresses are correct
- Check logs for "Failed to send" errors

### Issue: Database not updating
**Solution**:
- Verify SQL script applied
- Check Supabase connection
- Check logs for RPC errors

### Issue: Can't stop emergency mode
**Solution**:
- Use Dashboard button
- Use Grace/Control window button
- Check PIN is correct (if configured)

## Success Criteria

✅ **Emergency mode is working correctly if:**
1. Grace period window opens
2. Emergency activates after countdown
3. Data collected every 30 seconds
4. Emails sent to ALL recipients every 30 seconds
5. Database updates every 30 seconds
6. Can stop with PIN
7. Can restart after stopping
8. No "permission denied" errors

## Log File Analysis

**Good logs look like:**
```
INFO: Emergency Alert Triggered! Starting 5 second grace period...
INFO: EMERGENCY: Starting continuous emergency capture protocol...
INFO: EMERGENCY: Buffered screen_record chunk
INFO: EMERGENCY: Buffered camera chunk
INFO: EMERGENCY: Sent UPDATE #1 to admin@email.com
INFO: EMERGENCY: Sent UPDATE #1 to user@email.com
INFO: EMERGENCY: Updated alert record #123 via RPC
INFO: EMERGENCY: User requested to stop emergency mode
INFO: EMERGENCY: Sent STOPPED to admin@email.com
INFO: EMERGENCY MODE: Restored original feature permissions
```

**Bad logs look like:**
```
ERROR: permission denied for table emergency_alerts
ERROR: Failed to update alert record
ERROR: SMTP authentication failed
ERROR: name 'max_duration_minutes' is not defined
```

## Next Steps After Testing

If all tests pass:
- ✅ Emergency mode is production-ready
- ✅ Document any custom configurations
- ✅ Train users on how to use it

If tests fail:
- Check which test failed
- Review logs for errors
- Consult troubleshooting section
- Ask for help with specific error messages
