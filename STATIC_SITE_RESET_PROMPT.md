# Prompt: Add Password Reset to Existing Static Website

I have a simple static website deployed on Vercel with this structure:
```
/
├── index.html
├── script.js
├── style.css
└── admin/
    ├── index.html
    ├── admin.js
    └── admin.css
```

I need to add **Password Reset functionality** to the main `index.html` page.
When a user clicks a "Reset Password" link from an email, they land on my site with a URL like:
`https://mysite.vercel.app/#access_token=...&type=recovery`

## **Task Requirements**

1.  **Modify `index.html`**:
    *   Add the Supabase JS Client via CDN: `<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>`
    *   Add a **hidden** "Reset Password Modal" or Section. It should contain:
        *   A header "Set New Password".
        *   An input field for the new password.
        *   A "Save" button.

2.  **Modify `script.js`**:
    *   Initialize the Supabase client (I will provide keys).
    *   Add a listener for `supabase.auth.onAuthStateChange`.
    *   **Logic:**
        *   If the event is `PASSWORD_RECOVERY`, **hide** the normal landing page content and **show** the Reset Password Modal.
    *   Add a function `updatePassword()` that calls `supabase.auth.updateUser({ password: ... })`.
    *   Show success/error alerts.

3.  **Style via `style.css`**:
    *   Add simple styles for the modal so it looks good (centered, clean).

## **Output Needed**
Please provide the **exact code blocks** to add to:
1.  `index.html` (Where to paste the modal).
2.  `script.js` (The logic).
3.  `style.css` (The classes).

---
*Note: Make sure the Code fits seamlessly into a standard landing page structure.*
