# How Email Validation Works

## **Email Validation Explained**

The system checks email format using a **regex pattern** (regular expression).

---

## **The Pattern**

```python
pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
```

### **What This Means:**

```
^                           Start of email
[a-zA-Z0-9._%+-]+          Username part (before @)
@                           Must have @ symbol
[a-zA-Z0-9.-]+             Domain name (after @)
\.                          Must have a dot
[a-zA-Z]{2,}               Extension (.com, .org, etc.)
$                           End of email
```

---

## **Step-by-Step Check**

### **Example 1: Valid Email**
```
Email: "john.doe@example.com"

Step 1: Check if empty → No ✅
Step 2: Check pattern:
  - Username: "john.doe" → Has letters and dot ✅
  - @ symbol: "@" → Present ✅
  - Domain: "example" → Has letters ✅
  - Dot: "." → Present ✅
  - Extension: "com" → 2+ letters ✅

Result: VALID ✅
```

### **Example 2: Invalid Email (No @)**
```
Email: "johndoe.com"

Step 1: Check if empty → No ✅
Step 2: Check pattern:
  - @ symbol: Missing ❌

Result: INVALID ❌
Error: "Invalid email format. Example: user@example.com"
```

### **Example 3: Invalid Email (No Extension)**
```
Email: "john@example"

Step 1: Check if empty → No ✅
Step 2: Check pattern:
  - Username: "john" → ✅
  - @ symbol: "@" → ✅
  - Domain: "example" → ✅
  - Dot: Missing ❌
  - Extension: Missing ❌

Result: INVALID ❌
Error: "Invalid email format. Example: user@example.com"
```

### **Example 4: Invalid Email (Special Characters)**
```
Email: "john@doe@example.com"

Step 1: Check if empty → No ✅
Step 2: Check pattern:
  - Multiple @ symbols ❌

Result: INVALID ❌
Error: "Invalid email format. Example: user@example.com"
```

---

## **What's Allowed**

### **Username (before @):**
- ✅ Letters: a-z, A-Z
- ✅ Numbers: 0-9
- ✅ Special chars: . _ % + -
- ✅ Example: john.doe+test_123

### **Domain (after @, before .):**
- ✅ Letters: a-z, A-Z
- ✅ Numbers: 0-9
- ✅ Special chars: . -
- ✅ Example: mail.google

### **Extension (after .):**
- ✅ Letters only: a-z, A-Z
- ✅ Minimum 2 characters
- ✅ Examples: com, org, co.uk, info

---

## **Valid Email Examples**

```
✅ user@example.com
✅ john.doe@company.org
✅ test+tag@mail.co.uk
✅ admin_123@domain.info
✅ contact@sub.domain.com
```

---

## **Invalid Email Examples**

```
❌ invalid              (no @ or domain)
❌ user@                (no domain)
❌ @example.com         (no username)
❌ user@domain          (no extension)
❌ user @domain.com     (space in username)
❌ user@domain .com     (space in domain)
❌ user@@domain.com     (double @)
```

---

## **How It's Used in the App**

### **When You Click Save:**

```python
# 1. Get email from input field
email = self.entry_emergency_email.get().strip()

# 2. Check if email is entered
if email:
    # 3. Validate format
    is_valid, error = validate_email(email)
    
    # 4. If invalid, show error and stop
    if not is_valid:
        messagebox.showerror("Invalid Emergency Email", error)
        return  # Don't save
    
    # 5. If valid, continue saving
    self.settings["emergency"]["emergency_email"] = email
```

---

## **Error Messages**

### **Empty Email:**
```
Error: "Email cannot be empty"
```

### **Invalid Format:**
```
Error: "Invalid email format. Example: user@example.com"
```

---

## **Testing**

### **Test 1: Valid Email**
```
Enter: "test@gmail.com"
Click Save → ✅ Accepted
```

### **Test 2: No @ Symbol**
```
Enter: "testgmail.com"
Click Save → ❌ Error: "Invalid email format"
```

### **Test 3: No Extension**
```
Enter: "test@gmail"
Click Save → ❌ Error: "Invalid email format"
```

### **Test 4: Spaces**
```
Enter: "test @gmail.com"
Click Save → ❌ Error: "Invalid email format"
```

### **Test 5: Multiple @**
```
Enter: "test@@gmail.com"
Click Save → ❌ Error: "Invalid email format"
```

---

## **Summary**

The email validator checks:
1. ✅ Not empty
2. ✅ Has username before @
3. ✅ Has @ symbol
4. ✅ Has domain after @
5. ✅ Has dot (.)
6. ✅ Has extension (2+ letters)
7. ✅ No invalid characters
8. ✅ Proper format

**If any check fails → Shows error and prevents saving!** 🎯
