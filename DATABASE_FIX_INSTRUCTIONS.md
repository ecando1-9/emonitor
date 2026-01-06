# Emergency Mode Database Permission Fix - Action Required

## Problem Summary
You were getting these errors:
1. ❌ `permission denied for table emergency_alerts` - when updating email status flags
2. ❌ `permission denied for table emergency_alerts` - when updating emergency contact notifications  
3. ❌ `permission denied for table emergency_alerts` - when updating periodic location/activity data
4. ❌ `name 'max_duration_minutes' is not defined` - causing emergency mode to crash
5. ❌ Grace period window not opening after stopping emergency mode

**Result**: Emergency mode would crash, database wouldn't update, and you couldn't restart emergency mode.

## What I Fixed

### 1. Code Fixes (✅ Already Applied)
- ✅ Fixed the missing `max_duration_minutes` variable
- ✅ Fixed grace period window management (properly destroys old instances)
- ✅ Fixed `alert_in_progress` flag clearing when emergency stops
- ✅ Updated code to use **4 secure RPC functions** instead of direct database updates:
  - `increment_sender_assigned_count` - for SMTP sender management
  - `update_emergency_contacts_notified` - for emergency contact notifications
  - `update_emergency_email_status` - for email delivery tracking
  - `update_emergency_alert_periodic` - for 30-second location/activity updates

### 2. Database Fix (⚠️ YOU MUST RUN THIS)

**IMPORTANT: You must run the SQL script in your Supabase database**

#### Steps to Apply the Fix:

1. **Open Supabase Dashboard**
   - Go to your Supabase project
   - Navigate to the SQL Editor

2. **Run the SQL Script**
   - Open the file: `fix_sender_pool_rls.sql`
   - Copy ALL the contents
   - Paste into Supabase SQL Editor
   - Click "Run" or press Ctrl+Enter

3. **Verify Success**
   - You should see "Success. No rows returned"
   - Run this verification query:
   ```sql
   SELECT has_function_privilege('authenticated', 'update_emergency_contacts_notified(bigint, jsonb, integer)', 'execute');
   ```
   - It should return `true`

## What This Fix Does (Security Explanation)

### Secure Architecture
The fix implements **FOUR SECURITY DEFINER functions** - the most secure way to handle database updates:

#### 1. `increment_sender_assigned_count(sender_id)`
- **Purpose**: Track how many users are assigned to each SMTP sender
- **Security**: Runs with elevated privileges to bypass RLS
- **Why Safe**: Only increments a counter, no sensitive data access

#### 2. `update_emergency_contacts_notified(alert_id, contacts, count)`
- **Purpose**: Record which emergency contacts were successfully notified
- **Security**: Verifies you OWN the alert before allowing updates
- **Why Safe**: Only updates notification tracking fields

#### 3. `update_emergency_email_status(alert_id, email_status)`
- **Purpose**: Track email delivery status (sent to user, sent to admin, timestamps)
- **Security**: Verifies you OWN the alert before allowing updates  
- **Why Safe**: Only updates email tracking fields, cannot modify user data

#### 4. `update_emergency_alert_periodic(alert_id, alert_data)` ⭐ NEW
- **Purpose**: Update location, activity, and other data every 30 seconds during active emergency
- **Security**: Verifies you OWN the alert before allowing updates
- **Why Safe**: Only updates tracking fields, preserves data integrity

### Why This Is Very Secure

✅ **Prevents Unauthorized Access**: Users can ONLY update their own alerts  
✅ **Prevents Data Tampering**: Limited to specific tracking fields only  
✅ **Audit Trail**: All updates go through controlled functions  
✅ **No SQL Injection**: Uses parameterized queries  
✅ **Follows Principle of Least Privilege**: Minimal permissions granted  
✅ **No Direct Table Access**: Your app CANNOT directly UPDATE the tables

### Database Fields That Get Updated

When you trigger emergency mode, these fields are automatically populated:

**Initial Insert** (when emergency starts):
- ✅ `user_id`, `device_hash`, `triggered_at`
- ✅ `user_name`, `user_email`, `user_phone`, `device_name`
- ✅ `last_location`, `activity_summary`
- ✅ `emergency_contacts` (array of contacts)
- ✅ `status` = "new"

**After Email Sent** (via RPC):
- ✅ `email_sent_to_user` = true/false
- ✅ `email_sent_to_admin` = true/false
- ✅ `email_sent_to_user_at` = timestamp
- ✅ `email_sent_to_admin_at` = timestamp
- ✅ `email_details` = {recipients, subject, sender}

**After Contacts Notified** (via RPC):
- ✅ `emergency_contacts_notified` = array of notified contacts
- ✅ `emergency_contacts_notified_count` = number

**During Emergency** (periodic updates):
- ✅ `last_location` = updated every 30 seconds
- ✅ `activity_summary` = updated every 30 seconds

## Testing After Fix

1. Run the SQL script in Supabase
2. Restart your application: `python main.py`
3. Trigger emergency mode
4. Check logs - you should see:
   - ✅ "Updated alert record with X emergency contacts notified"
   - ❌ NO "permission denied" errors

## If You Still See Errors

If after running the SQL you still see permission errors:

1. **Check your Supabase connection**
   - Make sure you're using the correct project
   - Verify your API keys are correct

2. **Check RLS is enabled**
   - Run: `SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public';`
   - Both `sender_pool` and `emergency_alerts` should show `rowsecurity = true`

3. **Contact me** - I'll help debug further

## Summary

**What you MUST do:**
1. ✅ Run `fix_sender_pool_rls.sql` in Supabase SQL Editor
2. ✅ Restart your application

**What I already did:**
1. ✅ Fixed the code crash (`max_duration_minutes`)
2. ✅ Updated code to use secure RPC functions
3. ✅ Created the secure SQL script

This is a **production-ready, secure solution** that follows database security best practices.
