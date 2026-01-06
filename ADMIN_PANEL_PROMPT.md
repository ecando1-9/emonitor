# Prompt for Web Admin Panel - Trial Settings Feature

---

## **Feature Request: Add Trial Settings Management**

I need to add a settings page in my web-based admin panel to control free trial configuration for new users.

### **Database Schema:**

The settings are stored in the `app_config` table in Supabase:

```sql
CREATE TABLE public.app_config (
  key text NOT NULL PRIMARY KEY,
  value text NOT NULL,
  description text,
  updated_at timestamp with time zone DEFAULT now(),
  updated_by uuid
);
```

### **Settings to Manage:**

1. **Free Trial Days** (`free_trial_days`)
   - Current value: "7"
   - Description: "Number of days for free trial"
   - Input type: Number (1-365)

2. **Auto-Create Trial** (`auto_create_trial`)
   - Current value: "true"
   - Description: "Automatically create trial on signup"
   - Input type: Toggle/Checkbox (true/false)

### **Requirements:**

1. **Settings Page UI:**
   - Page title: "Trial Settings"
   - Two input fields:
     - Number input for trial days (min: 1, max: 365)
     - Toggle/checkbox for auto-create trial
   - Save button
   - Show last updated time
   - Show success/error messages

2. **Functionality:**
   - Fetch current values from `app_config` table on page load
   - Update `app_config` table when user clicks Save
   - Update `updated_at` timestamp
   - Store `updated_by` with current admin user ID
   - Show confirmation message after successful save

3. **SQL Queries Needed:**

**Fetch current settings:**
```sql
SELECT key, value, description, updated_at
FROM public.app_config
WHERE key IN ('free_trial_days', 'auto_create_trial');
```

**Update trial days:**
```sql
UPDATE public.app_config
SET value = '14', updated_at = now(), updated_by = 'admin-user-id'
WHERE key = 'free_trial_days';
```

**Update auto-create:**
```sql
UPDATE public.app_config
SET value = 'true', updated_at = now(), updated_by = 'admin-user-id'
WHERE key = 'auto_create_trial';
```

### **Example UI (React/Next.js):**

```jsx
import { useState, useEffect } from 'react';
import { supabase } from '@/lib/supabase';

export default function TrialSettings() {
  const [trialDays, setTrialDays] = useState(7);
  const [autoCreate, setAutoCreate] = useState(true);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  // Fetch current settings
  useEffect(() => {
    async function fetchSettings() {
      const { data } = await supabase
        .from('app_config')
        .select('key, value')
        .in('key', ['free_trial_days', 'auto_create_trial']);
      
      data?.forEach(item => {
        if (item.key === 'free_trial_days') {
          setTrialDays(parseInt(item.value));
        }
        if (item.key === 'auto_create_trial') {
          setAutoCreate(item.value === 'true');
        }
      });
    }
    fetchSettings();
  }, []);

  // Save settings
  async function handleSave() {
    setLoading(true);
    setMessage('');

    try {
      // Update trial days
      await supabase
        .from('app_config')
        .update({ 
          value: trialDays.toString(),
          updated_at: new Date()
        })
        .eq('key', 'free_trial_days');

      // Update auto-create
      await supabase
        .from('app_config')
        .update({ 
          value: autoCreate ? 'true' : 'false',
          updated_at: new Date()
        })
        .eq('key', 'auto_create_trial');

      setMessage('Settings saved successfully!');
    } catch (error) {
      setMessage('Error saving settings: ' + error.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-2xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">Trial Settings</h1>
      
      <div className="space-y-6">
        {/* Trial Days Input */}
        <div>
          <label className="block text-sm font-medium mb-2">
            Free Trial Days
          </label>
          <input
            type="number"
            min="1"
            max="365"
            value={trialDays}
            onChange={(e) => setTrialDays(parseInt(e.target.value))}
            className="w-full px-4 py-2 border rounded-lg"
          />
          <p className="text-sm text-gray-500 mt-1">
            Number of days new users get free trial (1-365)
          </p>
        </div>

        {/* Auto-Create Toggle */}
        <div>
          <label className="flex items-center space-x-3">
            <input
              type="checkbox"
              checked={autoCreate}
              onChange={(e) => setAutoCreate(e.target.checked)}
              className="w-5 h-5"
            />
            <span className="text-sm font-medium">
              Automatically create trial on signup
            </span>
          </label>
          <p className="text-sm text-gray-500 mt-1">
            If disabled, admins must manually assign subscriptions
          </p>
        </div>

        {/* Save Button */}
        <button
          onClick={handleSave}
          disabled={loading}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Saving...' : 'Save Settings'}
        </button>

        {/* Message */}
        {message && (
          <div className={`p-4 rounded-lg ${
            message.includes('Error') ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
          }`}>
            {message}
          </div>
        )}
      </div>
    </div>
  );
}
```

### **Example UI (HTML/JavaScript):**

```html
<!DOCTYPE html>
<html>
<head>
  <title>Trial Settings</title>
  <style>
    .container { max-width: 600px; margin: 50px auto; padding: 20px; }
    .form-group { margin-bottom: 20px; }
    label { display: block; margin-bottom: 5px; font-weight: bold; }
    input[type="number"] { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
    button { padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
    button:hover { background: #0056b3; }
    .message { padding: 10px; margin-top: 20px; border-radius: 4px; }
    .success { background: #d4edda; color: #155724; }
    .error { background: #f8d7da; color: #721c24; }
  </style>
</head>
<body>
  <div class="container">
    <h1>Trial Settings</h1>
    
    <div class="form-group">
      <label>Free Trial Days:</label>
      <input type="number" id="trialDays" min="1" max="365" value="7">
      <small>Number of days new users get free trial (1-365)</small>
    </div>

    <div class="form-group">
      <label>
        <input type="checkbox" id="autoCreate" checked>
        Automatically create trial on signup
      </label>
      <small>If disabled, admins must manually assign subscriptions</small>
    </div>

    <button onclick="saveSettings()">Save Settings</button>
    
    <div id="message"></div>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
  <script>
    const supabase = supabase.createClient('YOUR_SUPABASE_URL', 'YOUR_SUPABASE_KEY');

    // Load current settings
    async function loadSettings() {
      const { data } = await supabase
        .from('app_config')
        .select('key, value')
        .in('key', ['free_trial_days', 'auto_create_trial']);
      
      data?.forEach(item => {
        if (item.key === 'free_trial_days') {
          document.getElementById('trialDays').value = item.value;
        }
        if (item.key === 'auto_create_trial') {
          document.getElementById('autoCreate').checked = item.value === 'true';
        }
      });
    }

    // Save settings
    async function saveSettings() {
      const trialDays = document.getElementById('trialDays').value;
      const autoCreate = document.getElementById('autoCreate').checked;
      const messageDiv = document.getElementById('message');

      try {
        await supabase
          .from('app_config')
          .update({ value: trialDays, updated_at: new Date() })
          .eq('key', 'free_trial_days');

        await supabase
          .from('app_config')
          .update({ value: autoCreate ? 'true' : 'false', updated_at: new Date() })
          .eq('key', 'auto_create_trial');

        messageDiv.className = 'message success';
        messageDiv.textContent = 'Settings saved successfully!';
      } catch (error) {
        messageDiv.className = 'message error';
        messageDiv.textContent = 'Error: ' + error.message;
      }
    }

    // Load on page load
    loadSettings();
  </script>
</body>
</html>
```

### **Testing:**

1. Open the settings page
2. Change trial days to 14
3. Click Save
4. Create a new user account in the desktop app
5. Check that user gets 14-day trial

### **Additional Features (Optional):**

- Show history of changes (audit log)
- Preview: "New users will get X days trial"
- Validation: Prevent invalid values
- Confirmation dialog before saving
- Display current active trials count

---

**Please implement this trial settings management page in the admin panel.**
