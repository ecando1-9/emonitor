# Security Vulnerabilities & Fixes

## 🔴 CRITICAL VULNERABILITIES

### 1. **Subprocess Command Injection Risk** ⚠️ MEDIUM
**Location:** `ui/data_viewer_ui.py:131`
```python
subprocess.Popen(f'explorer /select,"{os.path.normpath(save_path)}"')
```
**Issue:** While `os.path.normpath` helps, using f-strings with subprocess can be risky if path contains special characters.
**Fix:** Use `subprocess.Popen` with list arguments or `shlex.quote()` for shell commands.

### 2. **Settings File Location** ⚠️ MEDIUM
**Location:** `config.py:5`
```python
CONFIG_FILE = 'settings.json'
```
**Issue:** Settings file stored in application directory (writable by any user with app access).
**Risk:** If app runs with elevated privileges, settings accessible to other users.
**Fix:** Store in user-specific directory (e.g., `%APPDATA%\eMonitor\settings.json` on Windows).

### 3. **Plaintext Encryption Password Storage** ⚠️ MEDIUM
**Location:** `config.py:40`
```python
"encryption_password": "",
```
**Issue:** Encryption password stored in plaintext in `settings.json`.
**Risk:** Anyone with file system access can read the password.
**Mitigation:** File is local, but should use OS keychain or encrypted storage.
**Fix:** Use Windows Credential Manager or encrypt the password field.

## 🟡 MEDIUM VULNERABILITIES

### 4. **Path Traversal Risk** ⚠️ LOW-MEDIUM
**Location:** `scheduler.py:162`, `ui/data_viewer_ui.py:109`
**Issue:** File paths from user input not fully validated for path traversal.
**Risk:** Malicious file names could access files outside intended directories.
**Fix:** Validate paths with `os.path.abspath()` and ensure they're within allowed directories.

### 5. **No Input Length Validation** ⚠️ LOW
**Location:** `ui/settings_ui.py`, `ui/login_ui.py`
**Issue:** Some input fields don't have maximum length limits.
**Risk:** Potential DoS via extremely long inputs.
**Fix:** Add maximum length validation for all text inputs.

### 6. **Log File May Contain Sensitive Data** ⚠️ LOW
**Location:** `logger_setup.py`, `sender.py:46`
**Issue:** Log files may contain error messages with sensitive data.
**Risk:** If log files are shared, sensitive info could leak.
**Fix:** Sanitize log output, ensure no passwords/tokens are logged.

## 🟢 LOW RISK / BEST PRACTICES

### 7. **Refresh Token Storage**
**Status:** Acceptable for desktop app, but could be improved.
**Recommendation:** Use OS keychain for token storage.

### 8. **No Rate Limiting on Login**
**Status:** Handled by Supabase (server-side).
**Recommendation:** Add client-side rate limiting for better UX.

### 9. **Emergency Email Hardcoded**
**Location:** `emergency_alert_manager.py:17`
```python
EMERGENCY_EMAIL = "ecando976@gmail.com"
```
**Status:** Acceptable for emergency feature.
**Recommendation:** Make configurable via settings.

## ✅ SECURE PRACTICES FOUND

1. ✅ **Strong Encryption**: AES-GCM 256-bit with PBKDF2 (100,000 iterations)
2. ✅ **Password Hashing**: PIN hashed with PBKDF2 and salt
3. ✅ **No Hardcoded Secrets**: API keys loaded from `.env`
4. ✅ **HTTPS Only**: All API calls use HTTPS (Supabase)
5. ✅ **Input Validation**: Most inputs validated (time format, email, etc.)
6. ✅ **SQL Injection Protection**: Using Supabase client (parameterized queries)
7. ✅ **Session Management**: Tokens properly cleared on logout
8. ✅ **Feature Access Control**: Server-side validation of plan features

## 🔧 RECOMMENDED FIXES

### Priority 1 (High)
1. Move settings file to user-specific directory
2. Fix subprocess command injection risk
3. Add path traversal protection

### Priority 2 (Medium)
4. Encrypt sensitive fields in settings.json
5. Add input length validation
6. Sanitize log output

### Priority 3 (Low)
7. Use OS keychain for tokens
8. Make emergency email configurable
9. Add rate limiting feedback

## 📊 OVERALL SECURITY RATING: **B+ (Good with room for improvement)**

The application follows many security best practices but has some areas that need attention, particularly around local data storage and input validation.

