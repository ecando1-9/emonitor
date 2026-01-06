# Feature Request: Password Reset Handling for eMonitor

I need to add a "Password Reset" page to our website (`https://ecantechesolutions.vercel.app`) to handle password recovery links from Supabase Auth.

## **The Flow**
1. User clicks "Forgot Password" in our Desktop App.
2. They receive an email with a link like:
   `https://ecantechesolutions.vercel.app/#access_token=...&refresh_token=...&type=recovery`
3. When they click this link, our website should render a "New Password" form instead of the homepage.

## **Implementation Details**

### **1. Detect Recovery Mode**
Use the Supabase JS Client to listen for the `PASSWORD_RECOVERY` event on page load.

```javascript
import { createClient } from '@supabase/supabase-js'

const supabase = createClient('YOUR_URL', 'YOUR_KEY')

supabase.auth.onAuthStateChange(async (event, session) => {
  if (event === "PASSWORD_RECOVERY") {
    // Show the "Update Password" UI modal or redirect to /reset-password page
    showResetPasswordForm();
  }
})
```

### **2. Update Password Function**
When the user submits the new password, call:

```javascript
const { data, error } = await supabase.auth.updateUser({
  password: new_password
})

if (error) {
  alert("Error: " + error.message)
} else {
  alert("Password updated successfully! You can now login to the Desktop App.")
}
```

## **Requirements**
- The form should be simple: One input field "New Password" and a "Save" button.
- It should only appear if the URL contains the recovery token.
- After success, show a confirmation message.

---

**Please implement this logic on the landing page or a dedicated route.**
