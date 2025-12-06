# How to Add a Sender Email to eMonitor

The error you're seeing means the `sender_pool` table in your Supabase database is empty. You need to add at least one sender email before eMonitor can send monitoring data.

## Method 1: Using the Python Script (Easiest)

1. **Navigate to the eMonitor folder:**
   ```powershell
   cd C:\Users\yuvak\Downloads\ecantech_esolutions\projects\emoniter
   ```

2. **Run the sender pool manager script:**
   ```powershell
   python add_sender_to_pool.py
   ```

3. **Select option 1 to add a new sender** and follow the prompts:
   - **SMTP Server**: `smtp.gmail.com` (for Gmail) or your email provider's SMTP server
   - **SMTP Port**: `587` (for most providers, 465 for secure)
   - **Sender Email**: Your email address (e.g., `myapp@gmail.com`)
   - **Sender Password**: Your app password (NOT your regular password!)
   - **Max Users**: How many eMonitor instances can use this sender (default 100)

4. **Verify it was added:**
   - Select option 2 to see all senders in the pool
   - Confirm the sender shows `Active: YES`

## Method 2: Using Gmail App Password

For Gmail specifically:

1. Enable 2-factor authentication on your Google account
2. Go to Google Account → Security → App passwords
3. Generate an app password for "Mail" and "Windows"
4. Copy the 16-character password
5. Use this password when prompted by the script

## Method 3: Using the Admin Panel (Node.js)

If you prefer using the Node.js admin panel:

1. Navigate to the admin panel:
   ```powershell
   cd .\admin_panel
   ```

2. Install dependencies:
   ```powershell
   npm install
   ```

3. Run the admin tool:
   ```powershell
   npm start
   ```

4. Select option 1 to add a new sender

## Troubleshooting

**"No SMTP sender available" error:**
- Make sure you added at least one sender
- Verify the sender has `is_active = true`
- Run the script with option 2 to list and check

**"Connection failed" error:**
- Verify `.env` file has `SUPABASE_URL` and `SUPABASE_ANON_KEY`
- Check your internet connection
- Try restarting the script

**After adding a sender, eMonitor still won't start:**
- Restart eMonitor completely
- The app caches the sender list, so it may need a restart to pick up new senders

## Example Configuration

For Gmail:
```
SMTP Server: smtp.gmail.com
SMTP Port: 587
Sender Email: your-email@gmail.com
Sender Password: xxxx xxxx xxxx xxxx  (16-char app password)
Max Users: 100
```

For Outlook/Office 365:
```
SMTP Server: smtp.office365.com
SMTP Port: 587
Sender Email: your-email@outlook.com
Sender Password: Your app password
Max Users: 100
```

---

Once you add a sender, run `python add_sender_to_pool.py` with option 2 to verify it appears in the pool, then restart eMonitor!
