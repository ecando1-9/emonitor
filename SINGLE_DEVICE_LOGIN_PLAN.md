# Single Device Login - Implementation Plan

## **Feature: Only One Device Login at a Time**

When user logs in on Device B, automatically logout from Device A.

---

## **How It Works**

### **Scenario:**
```
User logs in on Device A (Laptop)
  ↓
User is active on Device A ✅
  ↓
User logs in on Device B (Desktop)
  ↓
Device A automatically logged out ❌
Device B is now active ✅
```

---

## **Implementation**

### **Database: Track Active Sessions**

Add to `users` table:
```sql
ALTER TABLE public.users
ADD COLUMN active_device_hash text,
ADD COLUMN active_session_id text,
ADD COLUMN last_active timestamp with time zone;
```

### **On Login:**
```python
1. User logs in on Device B
2. Get Device B hash
3. Check if user has active session on different device
4. If yes:
   - Mark old session as invalid
   - Force logout on Device A
5. Save Device B as active device
6. Continue login on Device B
```

### **On App Start:**
```python
1. App checks if this device is the active device
2. If not:
   - Show message: "Logged out - Account active on another device"
   - Force logout
3. If yes:
   - Continue normally
```

---

## **Database Changes**

```sql
-- Add columns to users table
ALTER TABLE public.users
ADD COLUMN IF NOT EXISTS active_device_hash text,
ADD COLUMN IF NOT EXISTS active_session_id text,
ADD COLUMN IF NOT EXISTS last_active timestamp with time zone DEFAULT now();

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS users_active_device_idx ON public.users(active_device_hash);
```

---

## **Code Changes**

### **auth.py - On Login:**
```python
def sign_in(self, email, password):
    # ... existing login code ...
    
    if res.user:
        from device_fingerprint import get_device_hash
        current_device = get_device_hash()
        
        # Check if user is logged in on different device
        user_record = self.client.table("users").select("active_device_hash").eq("id", res.user.id).execute()
        
        if user_record.data:
            old_device = user_record.data[0].get("active_device_hash")
            
            if old_device and old_device != current_device:
                log.info(f"User logging in from new device. Old device: {old_device}, New device: {current_device}")
        
        # Update active device
        self.client.table("users").update({
            "active_device_hash": current_device,
            "active_session_id": res.session.access_token,
            "last_active": "now()"
        }).eq("id", res.user.id).execute()
        
        # Continue with login...
```

### **main.py - On App Start:**
```python
def check_active_session():
    """Check if this device has active session"""
    if auth_service.current_user:
        from device_fingerprint import get_device_hash
        current_device = get_device_hash()
        
        user_record = auth_service.client.table("users").select("active_device_hash").eq("id", auth_service.current_user.id).execute()
        
        if user_record.data:
            active_device = user_record.data[0].get("active_device_hash")
            
            if active_device != current_device:
                # This device is not active - force logout
                messagebox.showinfo(
                    "Session Ended",
                    "Your account is now active on another device.\nYou have been logged out."
                )
                auth_service.sign_out()
                return False
    
    return True
```

---

## **User Experience**

### **Device A (Old):**
```
User is working on Device A
  ↓
User logs in on Device B
  ↓
Device A detects session change
  ↓
Shows message: "Session Ended - Account active on another device"
  ↓
Automatically logs out ❌
```

### **Device B (New):**
```
User logs in on Device B
  ↓
Login successful ✅
  ↓
Device B is now the active device
  ↓
User can work normally
```

---

## **Benefits**

✅ **Security** - Prevents account sharing  
✅ **License Control** - One device per account  
✅ **Automatic** - No manual logout needed  
✅ **Clear Messages** - User knows why they were logged out  
✅ **Industry Standard** - Like Netflix, Spotify, etc.  

---

## **Similar To:**

- **Netflix**: "Your account is being used on another device"
- **Spotify**: "Your account is being used elsewhere"
- **Microsoft**: "You've been signed out because your account is in use on another device"

---

## **Next Steps**

1. Run SQL to add columns
2. Update auth.py for login tracking
3. Update main.py for session checking
4. Test with 2 devices

---

**This ensures only one device can be logged in at a time!** 🔒
