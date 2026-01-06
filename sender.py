import smtplib
import ssl
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
import time
import threading
import shutil
from logger_setup import log

from config import DATA_DIR

INSTANT_OUTBOX_DIR = os.path.join(DATA_DIR, "instant_outbox")

# --- Admin Log Sender Function (Unchanged) ---
def send_support_log(sender_config, admin_email, log_file_path):
    try:
        file_name = os.path.basename(log_file_path)
        subject = "eMonitor Support Log File"
        body = ("Attached is the application log file (emoniter.log) requested for review.\n\n"
            f"File: {file_name}")
        msg = MIMEMultipart()
        msg['From'] = sender_config['smtp_email']
        msg['To'] = admin_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        with open(log_file_path, "rb") as f:
            part = MIMEApplication(f.read(), Name=file_name)
        part['Content-Disposition'] = f'attachment; filename="{file_name}"'
        msg.attach(part)
        log.info(f"Connecting to {sender_config['smtp_server']} to send log file...")
        context = ssl.create_default_context()
        with smtplib.SMTP(
            sender_config['smtp_server'],
            int(sender_config['smtp_port'])
        ) as server:
            server.starttls(context=context)
            server.login(sender_config['smtp_email'], sender_config['smtp_password'])
            server.sendmail(sender_config['smtp_email'], admin_email, msg.as_string())
        log.info(f"Successfully sent log file to {admin_email}")
        return True
    except Exception as e:
        log.error(f"Error sending support log: {e}")
        return False

# --- !! NEW FEEDBACK SENDER FUNCTION !! ---
def send_feedback_email(sender_config, admin_email, user_email, feedback_message, log_file_path):
    """
    Sends the user's feedback message AND the log file to the admin.
    """
    try:
        subject = f"eMonitor Feedback from {user_email}"
        body = (
            "A user has submitted the following feedback:\n\n"
            "-------------------------------------------------\n"
            f"{feedback_message}\n"
            "-------------------------------------------------\n\n"
            "The user's application log (emoniter.log) is attached for debugging."
        )
        msg = MIMEMultipart()
        msg['From'] = sender_config['smtp_email']
        msg['To'] = admin_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        # Attach the log file
        if log_file_path and os.path.exists(log_file_path):
            with open(log_file_path, "rb") as f:
                part = MIMEApplication(f.read(), Name=os.path.basename(log_file_path))
            part['Content-Disposition'] = f'attachment; filename="emoniter.log"'
            msg.attach(part)
        
        log.info(f"Connecting to {sender_config['smtp_server']} to send feedback...")
        context = ssl.create_default_context()
        with smtplib.SMTP(
            sender_config['smtp_server'],
            int(sender_config['smtp_port'])
        ) as server:
            server.starttls(context=context)
            server.login(
                sender_config['smtp_email'],
                sender_config['smtp_password']
            )
            server.sendmail(
                sender_config['smtp_email'],
                admin_email,
                msg.as_string()
            )
        log.info(f"Successfully sent feedback to {admin_email}")
        return True
    except Exception as e:
        log.error(f"Error sending feedback email: {e}")
        return False

# --- Instant Sender Function (Unchanged) ---
def send_instant_report(sender_config, recipient_email, file_path):
    file_name = os.path.basename(file_path)
    log.info(f"Attempting INSTANT send: {file_name}")
    try:
        base_name = file_name.split('.')[0]
        subject = base_name
        body_intro = ""
        if file_name.endswith(".enc"):
            subject = f"{base_name} (High-Security)"
            body_intro = ("Attached is your end-to-end encrypted data report...")
        elif file_name.endswith(".zip"):
            subject = f"{base_name} (Password-Protected)"
            body_intro = ("Attached is your password-protected ZIP report...")
        else:
            subject = f"{base_name} (Unprotected)"
            body_intro = ("Attached is your unprotected data report...")
        msg = MIMEMultipart()
        msg['From'] = sender_config['smtp_email']
        msg['To'] = recipient_email
        msg['Subject'] = subject
        body = f"{body_intro}\n\nFile: {file_name}"
        msg.attach(MIMEText(body, 'plain'))
        with open(file_path, "rb") as f:
            part = MIMEApplication(f.read(), Name=file_name)
        part['Content-Disposition'] = f'attachment; filename="{file_name}"'
        msg.attach(part)
        context = ssl.create_default_context()
        with smtplib.SMTP(
            sender_config['smtp_server'],
            int(sender_config['smtp_port'])
        ) as server:
            server.starttls(context=context)
            server.login(sender_config['smtp_email'], sender_config['smtp_password'])
            server.sendmail(sender_config['smtp_email'], recipient_email, msg.as_string())
        log.info(f"Successfully sent instant report {file_name}.")
        try:
            os.remove(file_path)
        except Exception as e:
            log.error(f"Failed to delete sent instant file {file_name}: {e}")
    except Exception as e:
        log.warning(f"Instant send failed for {file_name}: {e}. Moving to instant_outbox.")
        try:
            if not os.path.exists(INSTANT_OUTBOX_DIR):
                os.makedirs(INSTANT_OUTBOX_DIR)
            shutil.move(file_path, os.path.join(INSTANT_OUTBOX_DIR, file_name))
        except Exception as move_e:
            log.error(f"CRITICAL: Failed to move {file_name} to instant_outbox: {move_e}")

# --- Bundle Sender Function (Unchanged) ---
def send_bundled_report(sender_config, recipient_email, file_list, device_name):
    log.info(f"Sending bundled report with {len(file_list)} files...")
    try:
        subject = f"eMonitor Report Bundle - {device_name} - {time.strftime('%Y-%m-%d %H:%M')}"
        body = (
            f"Attached is your bundled eMonitor report.\n\n"
            f"This email contains {len(file_list)} data files.\n\n"
            "NOTE: Password-protected ZIP files utilize AES-256 encryption for maximum security.\n"
            "The standard Windows extractor might show an error.\n"
            "Please use 7-Zip (Windows) or Keka/The Unarchiver (Mac) to open them.\n\n"
            "- eMonitor"
        )
        msg = MIMEMultipart()
        msg['From'] = sender_config['smtp_email']
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        for file_path in file_list:
            file_name = os.path.basename(file_path)
            try:
                with open(file_path, "rb") as f:
                    part = MIMEApplication(f.read(), Name=file_name)
                part['Content-Disposition'] = f'attachment; filename="{file_name}"'
                msg.attach(part)
            except Exception as e:
                log.error(f"Failed to attach file {file_name}: {e}")
        context = ssl.create_default_context()
        with smtplib.SMTP(
            sender_config['smtp_server'],
            int(sender_config['smtp_port'])
        ) as server:
            server.starttls(context=context)
            server.login(sender_config['smtp_email'], sender_config['smtp_password'])
            server.sendmail(sender_config['smtp_email'], recipient_email, msg.as_string())
        log.info(f"Successfully sent bundled report to {recipient_email}")
        return True
    except Exception as e:
        log.error(f"Error sending bundled report: {e}")
        return False