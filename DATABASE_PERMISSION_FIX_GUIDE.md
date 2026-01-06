# Database Permission Errors - Fix Guide

## Errors You're Seeing:

```
❌ ERROR: permission denied for table sender_pool
❌ ERROR: permission denied for table emergency_alerts
```

## What This Means:

Your emergency mode is **working correctly** (emails were sent successfully ✅), but the database cannot be updated because the **Row Level Security (RLS) policies** are missing.

### Impact:
- ✅ Emergency emails **ARE being sent** (working!)
- ✅ Emergency data **IS being collected** (working!)
- ❌ Database records **CANNOT be updated** (needs fix)
- ❌ Sender assignment count **CANNOT be tracked** (needs fix)

---

## How to Fix:

### Step 1: Open Supabase Dashboard
1. Go to [https://supabase.com](https://supabase.com)
2. Sign in to your account
3. Select your project

### Step 2: Open SQL Editor
1. Click on **"SQL Editor"** in the left sidebar
2. Click **"New Query"** button

### Step 3: Run the Fix Script
1. Open the file: `fix_sender_pool_rls.sql` (in your project folder)
2. **Copy ALL the contents** of the file
3. **Paste** into the Supabase SQL Editor
4. Click **"Run"** button (or press Ctrl+Enter)

### Step 4: Verify Success
You should see output like:
```
=== SENDER_POOL POLICIES ===
- Authenticated users can read sender_pool
- Authenticated users can update sender_pool assigned_count

=== EMERGENCY_ALERTS POLICIES ===
- Users can insert their own emergency alerts
- Users can view their own emergency alerts
- Users can update their own emergency alerts
- Service role can view all emergency alerts
```

---

## What the Fix Does:

### For `sender_pool` table:
✅ Allows authenticated users to **read** sender list  
✅ Allows authenticated users to **update** assigned_count  

### For `emergency_alerts` table:
✅ Allows users to **insert** their own emergency alerts  
✅ Allows users to **view** their own emergency alerts  
✅ Allows users to **update** their own emergency alerts  
✅ Allows admins to **view all** emergency alerts  

---

## After Running the Script:

### ✅ These errors will be FIXED:
- `permission denied for table sender_pool` → **RESOLVED**
- `permission denied for table emergency_alerts` → **RESOLVED**

### ✅ These features will work properly:
- Emergency alert status updates
- Sender assignment tracking
- Emergency contact notifications
- Database record keeping

---

## Testing:

After running the SQL script, test by:

1. **Trigger emergency mode** again
2. **Check logs** - you should see:
   - ✅ `Updated alert record #XX with iteration #YY`
   - ✅ `Updated assigned_count for sender...`
   - ❌ NO MORE "permission denied" errors

---

## Current Status (From Your Logs):

### ✅ What's Working:
- Emergency mode activation ✅
- Data collection (18 updates sent!) ✅
- Email sending to user ✅
- Email sending to emergency contact ✅
- Emergency mode stop ✅
- Screen recording lock management ✅

### ❌ What Needs Fixing:
- Database update permissions ❌ (run the SQL script)
- Sender pool tracking ❌ (run the SQL script)

---

## Important Notes:

1. **Emergency mode IS working** - emails are being sent successfully
2. **Only database updates are failing** - this doesn't stop emergency functionality
3. **The fix is simple** - just run the SQL script in Supabase
4. **One-time fix** - you only need to run this once

---

## Summary:

Your emergency mode successfully:
- ✅ Collected data for 18 iterations (9 minutes)
- ✅ Sent 18 updates to user email
- ✅ Sent 18 updates to emergency email
- ✅ Stopped cleanly when requested
- ✅ Released all locks properly

**Just run the SQL script to fix the database permission errors!**

---

## File Location:

The SQL fix script is located at:
```
c:\Users\yuvak\Downloads\ecantech_esolutions\projects\emoniter\fix_sender_pool_rls.sql
```

**Copy the entire contents and run in Supabase SQL Editor.**
