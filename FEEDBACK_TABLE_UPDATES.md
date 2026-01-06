# ✅ Feedback System Updates - SQL Table & Email Config

I have implemented the database table for storing user feedback and updated the email configuration as requested.

## 1. Supabase SQL Table

I created a SQL script to set up a robust `user_feedback` table in your Supabase database. This will store all user issues, bugs, and feature requests.

**Action Required:**
You MUST run the SQL script in your Supabase SQL Editor to create the table and functions.

1.  Copy the contents of `create_feedback_table.sql`.
2.  Go to your Supabase Dashboard → SQL Editor.
3.  Paste the SQL and click **Run**.

**Features:**
*   **Table**: `user_feedback` (stores email, message, device info, etc.)
*   **Security**: Row Level Security (RLS) enabled.
*   **Function**: `submit_user_feedback` (securely saves feedback via RPC).

## 2. Updated Feedback Logic (`ui/feedback_ui.py`)

I updated the `send_feedback` function in the app to:
1.  **Save to Database**: Calls `submit_user_feedback` to save to Supabase.
2.  **Log Attachment Option**: Added a checkbox so you can choose whether to attach the log file (`emoniter.log`). Checks are enabled by default.
3.  **Capture Metadata**: Captures device info (OS, version).
4.  **Send Email**: Sends email to `ecando976@gmail.com` (with or without log).

## 3. Email Configuration (`config.py`)

I updated the admin support email address as requested:
*   **Old**: `frdsconnect7799@gmail.com`
*   **New**: `ecando976@gmail.com`

All feedback emails will now be sent to `ecando976@gmail.com`.

## Verification

After applying the SQL script:
1.  Run the app.
2.  Login.
3.  Go to Dashboard → "Send Feedback / Report Issue".
4.  Type a test message (e.g., "This is a test bug report").
5.  Click Send.
6.  You should see:
    *   A success message in the app.
    *   A new row in your Supabase `user_feedback` table.
    *   An email in `ecando976@gmail.com`.
    *   Log entry: `INFO: Successfully sent feedback to ecando976@gmail.com`

## Files Changed
*   `create_feedback_table.sql` (Created)
*   `config.py` (Updated email)
*   `ui/feedback_ui.py` (Updated logic)
