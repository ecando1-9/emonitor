# User-Specific Settings - Solution

## Problem

Currently, settings are stored in `app_data/settings.json` on the device. When User A logs in, they configure settings. Then User B logs in on the same device and sees User A's settings instead of their own.

## Solution

Store user-specific settings in Supabase database, so each user has their own settings regardless of which device they use.

---

## Database Schema

Create a new table `user_settings` in Supabase:

```sql
CREATE TABLE IF NOT EXISTS public.user_settings (
  user_id uuid NOT NULL PRIMARY KEY,
  settings jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT user_settings_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE
);

ALTER TABLE public.user_settings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read their own settings"
  ON public.user_settings
  FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own settings"
  ON public.user_settings
  FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own settings"
  ON public.user_settings
  FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

GRANT SELECT, INSERT, UPDATE ON public.user_settings TO authenticated;

CREATE INDEX IF NOT EXISTS user_settings_user_id_idx ON public.user_settings(user_id);
```

---

## How It Works

### Current (Device-Based):
```
Device A:
  settings.json (shared by all users)
  User A logs in → Sees settings
  User B logs in → Sees same settings ❌
```

### New (User-Based):
```
Database:
  User A settings (stored in Supabase)
  User B settings (stored in Supabase)

Device A:
  User A logs in → Loads User A settings from database ✅
  User B logs in → Loads User B settings from database ✅
```

---

## Implementation

### 1. On Login (Fetch User Settings):

```python
# In auth.py, after successful login
def sign_in(self, email, password):
    # ... existing login code ...
    
    if res.user:
        # Fetch user settings from database
        settings_result = self.client.table("user_settings").select("settings").eq("user_id", res.user.id).execute()
        
        if settings_result.data and len(settings_result.data) > 0:
            # User has settings in database - use them
            user_settings = settings_result.data[0]["settings"]
            log.info("Loaded user settings from database")
        else:
            # First time login - create default settings
            default_settings = config_manager._get_default_settings()
            self.client.table("user_settings").insert({
                "user_id": res.user.id,
                "settings": default_settings
            }).execute()
            user_settings = default_settings
            log.info("Created new user settings in database")
        
        # Apply settings to local config
        config_manager.update_settings(user_settings)
```

### 2. On Settings Change (Save to Database):

```python
# In config.py
def save_settings(self):
    # Save locally (for offline use)
    try:
        with open(self.file_path, 'w') as f:
            json.dump(self.settings, f, indent=4)
        log.info("Settings saved locally.")
    except Exception as e:
        log.error(f"Error saving settings locally: {e}")
    
    # Save to database (if logged in)
    try:
        from auth import auth_manager
        if auth_manager.current_user:
            auth_manager.client.table("user_settings").update({
                "settings": self.settings,
                "updated_at": "now()"
            }).eq("user_id", auth_manager.current_user.id).execute()
            log.info("Settings synced to database.")
    except Exception as e:
        log.warning(f"Could not sync settings to database: {e}")
```

### 3. On Logout (Clear Local Settings):

```python
# In auth.py
def sign_out(self):
    # ... existing logout code ...
    
    # Clear local settings file
    config_manager.settings = config_manager._get_default_settings()
    config_manager.save_settings()
    log.info("Local settings cleared on logout")
```

---

## Benefits

✅ **User-Specific** - Each user has their own settings  
✅ **Cross-Device** - Settings follow user across devices  
✅ **Sync** - Changes saved to database automatically  
✅ **Offline** - Local file used as cache when offline  
✅ **Secure** - RLS ensures users only see their own settings  

---

## Migration

For existing users:
1. On first login after update, their local settings are uploaded to database
2. Future logins load from database
3. Local file becomes a cache

---

## Testing

1. **User A** logs in → Changes settings → Logs out
2. **User B** logs in on same device → Sees default settings (not User A's)
3. **User A** logs in again → Sees their own settings ✅
4. **User A** logs in on different device → Sees same settings ✅

---

This solves the problem of shared settings on the same device!
