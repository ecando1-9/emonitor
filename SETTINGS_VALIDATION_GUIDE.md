# Settings UI Validation - Implementation Guide

## Add These Validation Functions to settings_ui.py

Add at the top of the file (after imports):

```python
from validators import validate_email, validate_phone, validate_name

def validate_digits_only(P):
    """Validate that input contains only digits"""
    if P == "":
        return True
    return P.isdigit()

def validate_pin(P):
    """Validate PIN: only 4 digits"""
    if P == "":
        return True
    return P.isdigit() and len(P) <= 4
```

---

## Update Entry Fields with Validation

### 1. Phone Number Field (Line ~113)

**Before:**
```python
self.entry_user_phone = self._create_entry_row(phone_frame, "Your Phone Number:", ...)
```

**After:**
```python
# Create phone entry with digit-only validation
vcmd_phone = (self.register(validate_digits_only), '%P')
self.entry_user_phone = self._create_entry_row(
    phone_frame, 
    "Your Phone Number:", 
    self.settings.get("emergency", {}).get("user_phone", ""),
    validate=('key', vcmd_phone)
)
```

### 2. Emergency PIN Field

Find the PIN entry field and update:

**Before:**
```python
self.entry_pin = tk.Entry(...)
```

**After:**
```python
# PIN validation: only 4 digits
vcmd_pin = (self.register(validate_pin), '%P')
self.entry_pin = tk.Entry(
    ...,
    validate='key',
    validatecommand=vcmd_pin
)
```

### 3. Email Validation in handle_save()

Add to `handle_save()` method (before saving):

```python
def handle_save(self):
    # Validate emergency email
    emergency_email = self.entry_emergency_email.get().strip()
    if emergency_email:
        is_valid, error = validate_email(emergency_email)
        if not is_valid:
            messagebox.showerror("Invalid Email", error)
            return
    
    # Validate phone number
    phone = self.entry_user_phone.get().strip()
    if phone:
        is_valid, error = validate_phone(phone)
        if not is_valid:
            messagebox.showerror("Invalid Phone", error)
            return
    
    # Validate user name
    user_name = self.entry_user_name.get().strip()
    if user_name:
        is_valid, error = validate_name(user_name)
        if not is_valid:
            messagebox.showerror("Invalid Name", error)
            return
    
    # Validate emergency contacts
    for contact in self.emergency_contacts:
        # Validate contact email
        if contact['email']:
            is_valid, error = validate_email(contact['email'])
            if not is_valid:
                messagebox.showerror("Invalid Contact Email", 
                    f"Contact '{contact['name']}' has invalid email: {error}")
                return
        
        # Validate contact phone
        if contact['phone']:
            is_valid, error = validate_phone(contact['phone'])
            if not is_valid:
                messagebox.showerror("Invalid Contact Phone", 
                    f"Contact '{contact['name']}' has invalid phone: {error}")
                return
        
        # Validate contact name
        if contact['name']:
            is_valid, error = validate_name(contact['name'])
            if not is_valid:
                messagebox.showerror("Invalid Contact Name", error)
                return
    
    # Continue with save...
```

---

## Complete Example for _create_entry_row

Update the `_create_entry_row` method to support validation:

```python
def _create_entry_row(self, parent, label, default_value, show=None, validate=None):
    """Create a labeled entry row with optional validation"""
    row = tk.Frame(parent, bg="#2b2b2b")
    row.pack(fill="x", pady=2)
    
    lbl = tk.Label(row, text=label, bg="#2b2b2b", fg="white", width=20, anchor="w")
    lbl.pack(side="left", padx=5)
    
    entry_kwargs = {
        "bg": "#3c3c3c",
        "fg": "white",
        "insertbackground": "white"
    }
    
    if show:
        entry_kwargs["show"] = show
    
    if validate:
        entry_kwargs["validate"] = validate[0]
        entry_kwargs["validatecommand"] = validate[1]
    
    entry = tk.Entry(row, **entry_kwargs)
    entry.insert(0, default_value)
    entry.pack(side="left", fill="x", expand=True, padx=5)
    
    return entry
```

---

## Testing

### Phone Number:
- Type "123abc" → Only "123" appears ✅
- Type "1234567890" → Accepted ✅
- Type "abc" → Nothing appears ✅

### Emergency PIN:
- Type "1234" → Accepted ✅
- Type "12345" → Only "1234" appears ✅
- Type "abc" → Nothing appears ✅

### Email:
- Enter "invalid" → Error on save ✅
- Enter "valid@email.com" → Accepted ✅

### Name:
- Enter "John123" → Error on save ✅
- Enter "John Doe" → Accepted ✅

---

## Summary of Changes

1. ✅ Phone field - Only digits, no text
2. ✅ PIN field - Only 4 digits
3. ✅ Email validation - Proper format check
4. ✅ Name validation - No numbers/special chars
5. ✅ Contact validation - All fields validated

---

**This makes your settings form industry-standard!** 🎯
