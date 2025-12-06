python - <<'PY'
import os
print("SUPABASE_URL =", os.getenv("SUPABASE_URL"))
print("SUPABASE_ANON_KEY is set =", bool(os.getenv("SUPABASE_ANON_KEY")))
PY"""
Test script to diagnose email sending issues.
Run this script to check SMTP configuration and test email sending.
"""
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from logger_setup import log
from auth import auth_service
from config import config_manager
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def test_smtp_configuration():
    """Test SMTP configuration and attempt to send a test email"""
    print("\n" + "="*60)
    print("EMERGENCY EMAIL SENDING DIAGNOSTIC TEST")
    print("="*60 + "\n")
    
    # Check if user is logged in
    if not auth_service.current_user:
        print("❌ ERROR: User is not logged in!")
        print("   Please log in to the application first.\n")
        return False
    
    print(f"✅ User logged in: {auth_service.current_user.email}\n")
    
    # Check sender_pool
    print("1. Checking sender_pool table...")
    try:
        all_senders = auth_service.client.from_("sender_pool").select("*").execute()
        if all_senders.data:
            print(f"   Found {len(all_senders.data)} sender(s) in sender_pool:")
            active_senders = []
            for s in all_senders.data:
                is_active = s.get('is_active')
                status = "✅ ACTIVE" if is_active else "❌ INACTIVE"
                print(f"   - {s.get('smtp_email')}: {status} (is_active={is_active})")
                if is_active:
                    active_senders.append(s)
            
            if not active_senders:
                print("   ⚠️  WARNING: No active senders found in sender_pool!")
                print("   Fix: Set is_active = true for at least one sender in the database.\n")
            else:
                print(f"   ✅ Found {len(active_senders)} active sender(s)\n")
        else:
            print("   ❌ sender_pool table is EMPTY - no senders found\n")
    except Exception as e:
        print(f"   ❌ Error checking sender_pool: {e}\n")
    
    # Check config fallback
    print("2. Checking config fallback SMTP...")
    try:
        settings = config_manager.get_settings()
        smtp_config = settings.get("smtp", {})
        smtp_email = smtp_config.get("smtp_email", "")
        smtp_password = smtp_config.get("smtp_password", "")
        
        if smtp_email and smtp_password:
            print(f"   ✅ Config fallback SMTP found: {smtp_email}")
            print(f"   Server: {smtp_config.get('smtp_server', 'smtp.gmail.com')}")
            print(f"   Port: {smtp_config.get('smtp_port', 587)}\n")
        else:
            print("   ❌ Config fallback SMTP is NOT configured")
            print("   (smtp_email or smtp_password is empty)\n")
    except Exception as e:
        print(f"   ❌ Error checking config SMTP: {e}\n")
    
    # Try to get sender assignment
    print("3. Getting sender assignment...")
    try:
        creds_result = auth_service.get_sender_assignment(use_cache=False)
        if not creds_result.get("success"):
            error_msg = creds_result.get("error", "Unknown error")
            print(f"   ❌ Failed to get SMTP credentials: {error_msg}\n")
            print("   FIXES:")
            print("   1. Add SMTP credentials via admin panel (sender_pool table)")
            print("   2. Make sure at least one sender has is_active = true")
            print("   3. Or configure SMTP in settings.json\n")
            return False
        
        sender_config = creds_result.get("data")
        if not sender_config:
            print("   ❌ Sender config data is empty\n")
            return False
        
        print(f"   ✅ Got sender: {sender_config.get('smtp_email')}")
        print(f"   Server: {sender_config.get('smtp_server')}:{sender_config.get('smtp_port')}\n")
    except Exception as e:
        print(f"   ❌ Error getting sender assignment: {e}\n")
        import traceback
        traceback.print_exc()
        return False
    
    # Test sending email
    print("4. Testing email sending...")
    try:
        # Create test email
        msg = MIMEMultipart()
        msg['From'] = sender_config['smtp_email']
        msg['To'] = "ecando976@gmail.com"  # Test recipient
        msg['Subject'] = "TEST: Emergency Email Diagnostic"
        
        body = """This is a test email from the eMonitor emergency email diagnostic tool.

If you receive this email, your SMTP configuration is working correctly.

Test completed successfully!"""
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Validate required fields
        required_fields = ['smtp_server', 'smtp_port', 'smtp_email', 'smtp_password']
        missing_fields = [field for field in required_fields if not sender_config.get(field)]
        if missing_fields:
            print(f"   ❌ Sender config missing required fields: {missing_fields}\n")
            return False
        
        # Attempt to send
        print(f"   Connecting to {sender_config['smtp_server']}:{sender_config['smtp_port']}...")
        context = ssl.create_default_context()
        smtp_port = int(sender_config['smtp_port'])
        
        with smtplib.SMTP(sender_config['smtp_server'], smtp_port, timeout=30) as server:
            print("   Starting TLS...")
            server.starttls(context=context)
            print(f"   Logging in as {sender_config['smtp_email']}...")
            server.login(sender_config['smtp_email'], sender_config['smtp_password'])
            print("   Sending test email...")
            server.sendmail(sender_config['smtp_email'], ["ecando976@gmail.com"], msg.as_string())
        
        print("   ✅ SUCCESS! Test email sent successfully!")
        print("   Check ecando976@gmail.com inbox for the test email.\n")
        return True
        
    except smtplib.SMTPAuthenticationError as auth_error:
        print(f"   ❌ SMTP AUTHENTICATION FAILED!")
        print(f"   Error: {auth_error}")
        print("\n   COMMON FIXES:")
        print("   1. For Gmail: Use an App Password, not your regular password")
        print("   2. Enable 'Less secure app access' (if using regular password)")
        print("   3. Check that email and password are correct")
        print("   4. Make sure 2FA is enabled and you're using an App Password\n")
        return False
    except smtplib.SMTPException as smtp_error:
        print(f"   ❌ SMTP ERROR: {smtp_error}\n")
        return False
    except Exception as e:
        print(f"   ❌ UNEXPECTED ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\nStarting email diagnostic test...\n")
    success = test_smtp_configuration()
    
    print("="*60)
    if success:
        print("✅ DIAGNOSTIC COMPLETE: Email sending is working!")
    else:
        print("❌ DIAGNOSTIC COMPLETE: Email sending has issues - see above for fixes")
    print("="*60 + "\n")

