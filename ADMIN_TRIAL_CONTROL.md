# Admin Panel - Trial Control via app_config

## ✅ **Control Trial Settings in Real-Time**

Your admin panel can control trial settings using the existing `app_config` table!

---

## **How to Change Settings**

### **In Your Admin Panel:**

```sql
-- Change trial days to 14
UPDATE public.app_config
SET value = '14', updated_at = now()
WHERE key = 'free_trial_days';

-- Disable auto-trial
UPDATE public.app_config
SET value = 'false', updated_at = now()
WHERE key = 'auto_create_trial';

-- Enable auto-trial
UPDATE public.app_config
SET value = 'true', updated_at = now()
WHERE key = 'auto_create_trial';
```

---

## **Settings Format**

### **free_trial_days**
```
key: 'free_trial_days'
value: '7'  (or '14', '30', etc.)
description: 'Number of days for free trial'
```

### **auto_create_trial**
```
key: 'auto_create_trial'
value: 'true'  (or 'false')
description: 'Automatically create trial on signup'
```

---

## **Examples**

### **7-Day Trial (Default)**
```sql
UPDATE app_config SET value = '7' WHERE key = 'free_trial_days';
UPDATE app_config SET value = 'true' WHERE key = 'auto_create_trial';
```

### **14-Day Trial**
```sql
UPDATE app_config SET value = '14' WHERE key = 'free_trial_days';
```

### **30-Day Trial**
```sql
UPDATE app_config SET value = '30' WHERE key = 'free_trial_days';
```

### **Disable Auto-Trial**
```sql
UPDATE app_config SET value = 'false' WHERE key = 'auto_create_trial';
```

---

## **Admin Panel UI Example**

```html
<form>
  <label>Free Trial Days:</label>
  <input type="number" name="trial_days" value="7" min="1" max="365">
  
  <label>Auto-Create Trial:</label>
  <select name="auto_create">
    <option value="true">Enabled</option>
    <option value="false">Disabled</option>
  </select>
  
  <button>Save Settings</button>
</form>
```

```javascript
// Save settings
await supabase
  .from('app_config')
  .update({ 
    value: trialDays.toString(),
    updated_at: new Date() 
  })
  .eq('key', 'free_trial_days');

await supabase
  .from('app_config')
  .update({ 
    value: autoCreate ? 'true' : 'false',
    updated_at: new Date() 
  })
  .eq('key', 'auto_create_trial');
```

---

## **View Current Settings**

```sql
SELECT key, value, description, updated_at
FROM public.app_config
WHERE key IN ('free_trial_days', 'auto_create_trial');
```

**Result:**
```
key                  | value | description                      | updated_at
---------------------|-------|----------------------------------|------------
free_trial_days      | 7     | Number of days for free trial    | 2026-01-05
auto_create_trial    | true  | Automatically create trial...    | 2026-01-05
```

---

## **Testing**

### **Test 1: Change to 14 Days**
```sql
UPDATE app_config SET value = '14' WHERE key = 'free_trial_days';
```

Then signup new user → Check logs:
```
✅ Free trial created: 14 days (ends 2026-01-19)
```

### **Test 2: Disable Auto-Trial**
```sql
UPDATE app_config SET value = 'false' WHERE key = 'auto_create_trial';
```

Then signup new user → Check logs:
```
Auto-trial disabled by admin. User will need manual subscription assignment.
```

---

## **Benefits**

✅ **Uses existing table** - No new tables needed  
✅ **Simple values** - Just text strings (no JSON)  
✅ **Instant effect** - Next signup uses new settings  
✅ **Easy to manage** - Simple UPDATE queries  
✅ **Audit trail** - `updated_at` and `updated_by` tracked  

---

## **Summary**

**To change trial days:**
```sql
UPDATE app_config SET value = '14' WHERE key = 'free_trial_days';
```

**To disable auto-trial:**
```sql
UPDATE app_config SET value = 'false' WHERE key = 'auto_create_trial';
```

**Changes take effect immediately for new signups!** 🎉
