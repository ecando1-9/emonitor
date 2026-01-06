# Security & Validation Improvements

## Features to Implement

### 1. Strong Password Policy
- Minimum 8 characters
- At least 1 uppercase letter
- At least 1 lowercase letter
- At least 1 number
- At least 1 special character

### 2. Login Attempt Limit
- Max 5 failed attempts
- After 5 failures: 15-minute lockout
- Track attempts per email/device

### 3. Email Validation
- Check email format (regex)
- Verify email exists (optional - requires internet)
- Show error if invalid

### 4. Phone Number Validation
- Only numbers allowed
- Optional: country code format
- Min/max length

### 5. Name Validation
- Only letters and spaces
- No numbers or special characters
- Min 2 characters

---

## Implementation Files

1. `auth.py` - Password policy & login attempts
2. `ui/settings_ui.py` - Email, phone, name validation
3. `validators.py` - Validation functions (new file)

---

## Database Changes

Need to track login attempts:

```sql
CREATE TABLE public.login_attempts (
  id uuid DEFAULT gen_random_uuid(),
  email text NOT NULL,
  device_hash text,
  attempt_time timestamp with time zone DEFAULT now(),
  success boolean DEFAULT false,
  ip_address text,
  CONSTRAINT login_attempts_pkey PRIMARY KEY (id)
);

CREATE INDEX login_attempts_email_idx ON public.login_attempts(email);
CREATE INDEX login_attempts_device_hash_idx ON public.login_attempts(device_hash);
```
