# Security & Validation - Complete Implementation Guide

## ✅ **What's Been Created**

1. ✅ `validators.py` - Validation functions
2. ✅ `login_attempts_table.sql` - Database table for tracking attempts
3. ✅ This guide

---

## **Features Implemented**

### **1. Password Validation** ✅
```python
from validators import validate_password

is_valid, error = validate_password("MyPass123!")
if not is_valid:
    show_error(error)
```

**Requirements:**
- ✅ Minimum 8 characters
- ✅ At least 1 uppercase (A-Z)
- ✅ At least 1 lowercase (a-z)
- ✅ At least 1 number (0-9)
- ✅ At least 1 special character (!@#$%...)

### **2. Email Validation** ✅
```python
from validators import validate_email

is_valid, error = validate_email("user@example.com")
if not is_valid:
    show_error(error)
```

**Checks:**
- ✅ Valid email format
- ✅ Has @ symbol
- ✅ Has domain
- ✅ Has extension (.com, .org, etc.)

### **3. Phone Validation** ✅
```python
from validators import validate_phone

is_valid, error = validate_phone("1234567890")
if not is_valid:
    show_error(error)
```

**Checks:**
- ✅ Only digits (0-9)
- ✅ Length 10-15 digits
- ✅ Auto-removes separators (-, spaces, etc.)

### **4. Name Validation** ✅
```python
from validators import validate_name

is_valid, error = validate_name("John Doe")
if not is_valid:
    show_error(error)
```

**Checks:**
- ✅ Only letters, spaces, hyphens, apostrophes
- ✅ No numbers
- ✅ No special characters
- ✅ Minimum 2 characters

---

## **Implementation Steps**

### **Step 1: Run SQL** (Create login_attempts table)

```bash
# In Supabase Dashboard → SQL Editor
# Run: login_attempts_table.sql
```

### **Step 2: Update auth.py** (Add password validation & login attempts)

I'll create a separate file with the exact code changes needed.

### **Step 3: Update settings_ui.py** (Add input validation)

I'll create a separate file with the exact code changes needed.

### **Step 4: Test**

Test all validations work correctly.

---

## **Usage Examples**

### **In Signup (auth.py)**:
```python
from validators import validate_password, validate_email

def sign_up(self, email, password):
    # Validate email
    is_valid, error = validate_email(email)
    if not is_valid:
        return {"success": False, "error": error}
    
    # Validate password
    is_valid, error = validate_password(password)
    if not is_valid:
        return {"success": False, "error": error}
    
    # Continue with signup...
```

### **In Settings (settings_ui.py)**:
```python
from validators import validate_email, validate_phone, validate_name

def handle_save(self):
    # Validate emergency email
    email = self.entry_emergency_email.get()
    is_valid, error = validate_email(email)
    if not is_valid:
        messagebox.showerror("Invalid Email", error)
        return
    
    # Validate phone
    phone = self.entry_phone.get()
    is_valid, error = validate_phone(phone)
    if not is_valid:
        messagebox.showerror("Invalid Phone", error)
        return
    
    # Validate name
    name = self.entry_name.get()
    is_valid, error = validate_name(name)
    if not is_valid:
        messagebox.showerror("Invalid Name", error)
        return
    
    # Save settings...
```

### **Login Attempts Tracking**:
```python
from datetime import datetime, timedelta
from device_fingerprint import get_device_hash

def check_login_attempts(self, email):
    """Check if user is locked out due to too many failed attempts"""
    device_hash = get_device_hash()
    
    # Get failed attempts in last 15 minutes
    fifteen_min_ago = (datetime.now() - timedelta(minutes=15)).isoformat()
    
    result = self.client.table("login_attempts").select("*").eq("email", email).eq("success", False).gte("attempt_time", fifteen_min_ago).execute()
    
    failed_attempts = len(result.data) if result.data else 0
    
    if failed_attempts >= 5:
        return False, "Too many failed login attempts. Please wait 15 minutes and try again."
    
    return True, ""

def record_login_attempt(self, email, success):
    """Record login attempt"""
    device_hash = get_device_hash()
    
    try:
        self.client.table("login_attempts").insert({
            "email": email,
            "device_hash": device_hash,
            "success": success,
            "attempt_time": datetime.now().isoformat()
        }).execute()
    except:
        pass  # Don't fail login if logging fails
```

---

## **Error Messages**

### **Password Errors**:
- "Password cannot be empty"
- "Password must be at least 8 characters long"
- "Password must contain at least one uppercase letter"
- "Password must contain at least one lowercase letter"
- "Password must contain at least one number"
- "Password must contain at least one special character"

### **Email Errors**:
- "Email cannot be empty"
- "Invalid email format. Example: user@example.com"

### **Phone Errors**:
- "Phone number cannot be empty"
- "Phone number can only contain digits (0-9)"
- "Phone number must be 10-15 digits"

### **Name Errors**:
- "Name cannot be empty"
- "Name can only contain letters, spaces, hyphens, and apostrophes"
- "Name must be at least 2 characters"

### **Login Attempt Errors**:
- "Too many failed login attempts. Please wait 15 minutes and try again."

---

## **Testing Checklist**

### **Password Validation**:
- [ ] "weak" → Error
- [ ] "WeakPass" → Error (no number/special char)
- [ ] "weakpass123" → Error (no uppercase)
- [ ] "WEAKPASS123!" → Error (no lowercase)
- [ ] "WeakPass123!" → Success ✅

### **Email Validation**:
- [ ] "invalid" → Error
- [ ] "invalid@" → Error
- [ ] "invalid@domain" → Error
- [ ] "valid@domain.com" → Success ✅

### **Phone Validation**:
- [ ] "abc123" → Error
- [ ] "123" → Error (too short)
- [ ] "1234567890" → Success ✅
- [ ] "+1 (234) 567-8900" → Success ✅ (auto-cleaned)

### **Name Validation**:
- [ ] "J" → Error (too short)
- [ ] "John123" → Error (has numbers)
- [ ] "John@Doe" → Error (special chars)
- [ ] "John Doe" → Success ✅
- [ ] "Mary-Jane O'Connor" → Success ✅

### **Login Attempts**:
- [ ] 1st failed login → Allow
- [ ] 2nd failed login → Allow
- [ ] 3rd failed login → Allow
- [ ] 4th failed login → Allow
- [ ] 5th failed login → Allow
- [ ] 6th failed login → Block with error ✅
- [ ] Wait 15 minutes → Allow again ✅

---

## **Next Steps**

1. **Run SQL**: `login_attempts_table.sql`
2. **Integrate validators**: I'll create the exact code changes
3. **Test**: Use the checklist above
4. **Deploy**: Roll out to users

---

**This makes your app industry-standard secure!** 🔒
