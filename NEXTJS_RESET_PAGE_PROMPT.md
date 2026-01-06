# Prompt: Build a Secure Password Reset Page with Next.js & Supabase

I need to create a secure **Password Reset Page** for my project using **Next.js** (App Router) deployed on **Vercel**. This page handles the password recovery flow initiated from my Python Desktop App via Supabase Auth.

## **Context**
- **Trigger:** User clicks "Forgot Password" in Desktop App -> Receives Email -> Clicks Link.
- **Link Format:** `https://ecantechesolutions.vercel.app/reset-password#access_token=...&refresh_token=...&type=recovery`
- **Goal:** The user lands on this page, enters a new password, and it updates their account in Supabase.

## **Requirements**

### **1. Tech Stack**
- **Framework:** Next.js 14+ (App Router)
- **Styling:** Tailwind CSS (or CSS Modules)
- **Auth:** `@supabase/ssr` (or `@supabase/supabase-js` client-side)
- **Deployment:** Vercel

### **2. Environment Variables (Security)**
- Do NOT hardcode keys. Use Vercel Environment Variables:
  - `NEXT_PUBLIC_SUPABASE_URL`
  - `NEXT_PUBLIC_SUPABASE_ANON_KEY`

### **3. Functionality**
- **Route:** Create a page at `/reset-password` (or handle it on home `/`).
- **Token Detection:** Automatically detect the `#access_token` hash fragment from the URL.
- **Session Exchange:** Use Supabase's `onAuthStateChange` to capture the session.
- **UI:** 
  - Show a "Loading..." state while verifying token.
  - If valid: Show "New Password" input & "Save" button.
  - If invalid/expired: Show error message "Link expired".
- **Action:** updating the password using `supabase.auth.updateUser({ password: ... })`.
- **Feedback:** displaying success/error messages nicely.

## **Code Needed**
Please provide the full code for:
1. `app/reset-password/page.tsx` (The Reset UI)
2. `lib/supabase.ts` (Client initialization)
3. Instructions on how to set the Environment Variables in Vercel.

---

**Note:** Ensure the design is clean, professional, and responsive (mobile-friendly).
