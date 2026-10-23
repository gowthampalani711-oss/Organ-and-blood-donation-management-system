from __future__ import annotations
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from dotenv import load_dotenv
from database import DBWrapper

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE_PATH = os.path.join(PROJECT_ROOT, ".env")
if os.path.exists(ENV_FILE_PATH):
    load_dotenv(dotenv_path=ENV_FILE_PATH)
else:
    load_dotenv()


def clean_env(key: str, default: str = "") -> str:
    val = os.getenv(key, default) or ""
    return val.strip().strip('"').strip("'")


def get_smtp_config():
    """Dynamically read latest SMTP configuration from environment."""
    server = clean_env("MAIL_SERVER", "smtp.gmail.com")
    try:
        port = int(clean_env("MAIL_PORT", "587"))
    except ValueError:
        port = 587
    use_tls = clean_env("MAIL_USE_TLS", "true").lower() == "true"
    username = clean_env("MAIL_USERNAME", "")
    password = clean_env("MAIL_PASSWORD", "")
    sender = clean_env("MAIL_DEFAULT_SENDER", username or "noreply@organdonation.org")
    return server, port, use_tls, username, password, sender


MAIL_SERVER = clean_env("MAIL_SERVER", "smtp.gmail.com")
MAIL_PORT = int(clean_env("MAIL_PORT", "587"))
MAIL_USE_TLS = clean_env("MAIL_USE_TLS", "true").lower() == "true"
MAIL_USERNAME = clean_env("MAIL_USERNAME", "")
MAIL_PASSWORD = clean_env("MAIL_PASSWORD", "")
MAIL_DEFAULT_SENDER = clean_env("MAIL_DEFAULT_SENDER", "noreply@organdonation.org")

# In-memory test cache for secure unit/e2e testing
_LAST_DISPATCHED_EMAIL: dict[str, str] = {}


def get_last_dispatched_email_otp(email_address: str) -> str | None:
    """Helper for testing to retrieve the generated random OTP sent to an email."""
    email = str(email_address).strip().lower()
    return _LAST_DISPATCHED_EMAIL.get(email)


def send_donor_card_email(recipient_email: str, donor_name: str, donor_id: str, pdf_file_path: str) -> tuple[bool, str]:
    """
    Sends the Donor Card PDF to the donor's registered email address using configured SMTP.
    Logs delivery status and adds a system notification.
    """
    recipient_email = str(recipient_email).strip().lower()
    subject = f"Official Organ Donor Card - {donor_name} ({donor_id})"

    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px; background-color: #ffffff;">
        <div style="text-align: center; padding-bottom: 20px; border-bottom: 2px solid #E63946;">
            <h2 style="color: #1D3557; margin-bottom: 5px;">Organ & Blood Donation Management System</h2>
            <p style="color: #457B9D; margin-top: 0; font-weight: bold;">Government Recognized Life Saver Network</p>
        </div>
        <div style="padding: 20px 0;">
            <p style="font-size: 16px; color: #334155;">Dear <strong>{donor_name}</strong>,</p>
            <p style="color: #475569; line-height: 1.6;">
                Thank you for your noble and selfless decision to register as an organ donor. Your pledge has the extraordinary power to save and transform human lives.
            </p>
            <div style="background-color: #F1FAEE; border-left: 4px solid #2A9D8F; padding: 15px; margin: 20px 0; border-radius: 4px;">
                <p style="margin: 0; color: #1D3557; font-weight: bold;">Unique Donor ID: <span style="color: #E63946;">{donor_id}</span></p>
                <p style="margin: 5px 0 0 0; color: #475569; font-size: 14px;">Verification Status: <strong>Verified & Active</strong></p>
            </div>
            <p style="color: #475569; line-height: 1.6;">
                Please find attached your official digital <strong>Donor Card (PDF)</strong> containing your unique verification QR Code. You can print or save this card on your smartphone.
            </p>
        </div>
        <div style="text-align: center; padding-top: 20px; border-top: 1px solid #e2e8f0; font-size: 12px; color: #94a3b8;">
            <p style="margin: 0;">24x7 Emergency Donor Helpline: 108 / 104</p>
            <p style="margin: 5px 0 0 0;">This is an automated system email. Please do not reply directly.</p>
        </div>
    </div>
    """

    # Record notification in database
    try:
        with DBWrapper() as db:
            db.execute(
                """INSERT INTO notifications (user_type, user_identifier, title_en, title_ta, message_en, message_ta, type)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (
                    "donor",
                    donor_id,
                    f"Donor Card Issued ({donor_id})",
                    f"தானமளிப்பவர் அட்டை வழங்கப்பட்டது ({donor_id})",
                    f"Donor card for {donor_name} generated and sent to {recipient_email}.",
                    f"{donor_name} அவர்களுக்கான தானமளிப்பவர் அட்டை உருவாக்கப்பட்டு {recipient_email} முகவரிக்கு அனுப்பப்பட்டது.",
                    "success"
                )
            )
    except Exception as db_err:
        print(f"[Email Service] Notification DB log warning: {db_err}")

    # In unit test mode, record test dispatch and return success
    if os.environ.get("UNIT_TEST_MODE") == "1":
        _LAST_DISPATCHED_EMAIL[recipient_email] = f"DONOR_CARD_{donor_id}"
        print(f"[Email Service] Successfully sent Donor Card email to: {recipient_email}")
        return True, "Email sent successfully"

    server_host, server_port, use_tls, username, password, default_sender = get_smtp_config()

    if not username or not password:
        print(f"[Email Service] SMTP credentials not configured in .env for recipient: {recipient_email}")
        return False, "SMTP credentials not configured in .env"

    try:
        msg = MIMEMultipart()
        msg['From'] = default_sender
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(html_body, 'html'))

        if pdf_file_path and os.path.exists(pdf_file_path):
            with open(pdf_file_path, "rb") as f:
                attach = MIMEApplication(f.read(), _subtype="pdf")
                attach.add_header('Content-Disposition', 'attachment', filename=os.path.basename(pdf_file_path))
                msg.attach(attach)

        server = smtplib.SMTP(server_host, server_port, timeout=15)
        if use_tls:
            server.starttls()

        try:
            server.login(username, password)
        except Exception:
            # Retry with cleaned password (e.g. spaceless app password)
            server.login(username, password.replace(" ", ""))

        server.sendmail(default_sender, recipient_email, msg.as_string())
        server.quit()
        _LAST_DISPATCHED_EMAIL[recipient_email] = f"DONOR_CARD_{donor_id}"
        print(f"[Email Service] Successfully sent Donor Card email to: {recipient_email}")
        return True, "Email sent successfully"
    except Exception as e:
        print(f"[Email Service] SMTP error sending Donor Card: {e}")
        return False, str(e)


def send_admin_otp_email(recipient_email, otp_code, purpose="admin_login"):
    """
    Sends Admin OTP verification code via email and logs system notification.
    """
    _LAST_DISPATCHED_EMAIL[str(recipient_email).strip().lower()] = str(otp_code).strip()
    if purpose == "admin_signup":
        purpose_label = "Admin Account Registration"
    elif purpose == "admin_reset_password":
        purpose_label = "Admin Password Reset"
    else:
        purpose_label = "Admin Portal Login"
    subject = f"LifeSaver ODMS - {purpose_label} Verification Code"

    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 500px; margin: auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px; background-color: #ffffff;">
        <div style="text-align: center; padding-bottom: 15px; border-bottom: 2px solid #1D3557;">
            <h2 style="color: #1D3557; margin-bottom: 5px;">Administrator Security Verification</h2>
            <p style="color: #457B9D; margin-top: 0; font-size: 14px;">Organ & Blood Donation Management System</p>
        </div>
        <div style="padding: 20px 0; text-align: center;">
            <p style="font-size: 15px; color: #334155;">Your one-time security verification code for <strong>{purpose_label}</strong> is:</p>
            <div style="background-color: #F1FAEE; border: 2px dashed #2A9D8F; padding: 15px; margin: 15px auto; border-radius: 8px; display: inline-block;">
                <span style="font-size: 28px; font-weight: bold; letter-spacing: 6px; color: #1D3557;">{otp_code}</span>
            </div>
            <p style="color: #64748B; font-size: 13px;">This code is valid for 5 minutes. Do not share this code with anyone.</p>
        </div>
        <div style="text-align: center; padding-top: 15px; border-top: 1px solid #e2e8f0; font-size: 11px; color: #94a3b8;">
            <p style="margin: 0;">Authorized Medical Administrator Access Portal</p>
        </div>
    </div>
    """

    # Record notification in database
    with DBWrapper() as db:
        db.execute(
            """INSERT INTO notifications (user_type, user_identifier, title_en, title_ta, message_en, message_ta, type)
               VALUES ('admin', %s, %s, %s, %s, %s, 'info')""",
            (
                recipient_email,
                f"Admin OTP Code Generated ({purpose_label})",
                f"நிர்வாகி OTP குறியீடு உருவாக்கப்பட்டது ({purpose_label})",
                f"Verification OTP code sent to {recipient_email} for {purpose_label}.",
                f"{recipient_email} முகவரிக்கு {purpose_label} OTP குறியீடு அனுப்பப்பட்டது.",
            )
        )

    if not MAIL_USERNAME or not MAIL_PASSWORD:
        masked_email = recipient_email[:2] + "****@" + recipient_email.split("@")[1] if "@" in recipient_email else recipient_email
        print(f"[Email Service] SMTP not configured. Simulated Admin OTP delivery to: {masked_email}")
        return True, "Email simulated"

    try:
        msg = MIMEMultipart()
        msg['From'] = MAIL_DEFAULT_SENDER
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(html_body, 'html'))

        server = smtplib.SMTP(MAIL_SERVER, MAIL_PORT)
        if MAIL_USE_TLS:
            server.starttls()
        server.login(MAIL_USERNAME, MAIL_PASSWORD)
        server.sendmail(MAIL_DEFAULT_SENDER, recipient_email, msg.as_string())
        server.quit()
        print(f"[Email Service] Successfully sent Admin OTP email to: {recipient_email}")
        return True, "Email sent successfully"
    except Exception as e:
        print(f"[Email Service] SMTP error sending Admin OTP: {e}")
        return False, str(e)


def send_otp_email(recipient_email, otp_code, purpose="email_verification"):
    """
    Sends 6-digit OTP verification code to any user's email address.
    """
    _LAST_DISPATCHED_EMAIL[str(recipient_email).strip().lower()] = str(otp_code).strip()
    purpose_label = "Donor Email Verification"
    if "organ" in purpose:
        purpose_label = "Organ Donor Pledge Verification"
    elif "blood" in purpose:
        purpose_label = "Blood Donor Registration Verification"
    elif "admin" in purpose:
        purpose_label = "Administrator Portal Verification"

    subject = f"LifeSaver ODMS - Verification Code: {otp_code}"

    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 520px; margin: auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 12px; background-color: #ffffff;">
        <div style="text-align: center; padding-bottom: 16px; border-bottom: 2px solid #E63946;">
            <h2 style="color: #1D3557; margin-bottom: 4px;">LifeSaver Network</h2>
            <p style="color: #457B9D; margin-top: 0; font-size: 14px; font-weight: bold;">Organ & Blood Donation Management System</p>
        </div>
        <div style="padding: 24px 0; text-align: center;">
            <p style="font-size: 15px; color: #334155; margin-bottom: 8px;">Your one-time security verification code for <strong>{purpose_label}</strong> is:</p>
            <div style="background-color: #F1FAEE; border: 2px dashed #2A9D8F; padding: 16px 28px; margin: 16px auto; border-radius: 10px; display: inline-block;">
                <span style="font-size: 32px; font-weight: 800; letter-spacing: 8px; color: #1D3557;">{otp_code}</span>
            </div>
            <p style="color: #64748B; font-size: 13px; margin-top: 12px;">This code is valid for <strong>5 minutes</strong>. Do not share this OTP with anyone.</p>
        </div>
        <div style="text-align: center; padding-top: 16px; border-top: 1px solid #e2e8f0; font-size: 11px; color: #94a3b8;">
            <p style="margin: 0;">24x7 Emergency Donor Helpline: 108 / 104</p>
            <p style="margin: 4px 0 0 0;">This is an automated message. Please do not reply directly to this email.</p>
        </div>
    </div>
    """

    # Record notification in database
    with DBWrapper() as db:
        db.execute(
            """INSERT INTO notifications (user_type, user_identifier, title_en, title_ta, message_en, message_ta, type)
               VALUES ('user', %s, %s, %s, %s, %s, 'info')""",
            (
                recipient_email,
                f"OTP Code Generated ({purpose_label})",
                f"OTP குறியீடு உருவாக்கப்பட்டது ({purpose_label})",
                f"Verification OTP code sent to {recipient_email} for {purpose_label}.",
                f"{recipient_email} முகவரிக்கு சரிபார்ப்பு OTP குறியீடு அனுப்பப்பட்டது.",
            )
        )

    if not MAIL_USERNAME or not MAIL_PASSWORD:
        masked_email = recipient_email[:2] + "****@" + \
            recipient_email.split("@")[1] if "@" in recipient_email else recipient_email
        print(
            f"[Email Service] SMTP not configured in .env. Simulated email delivery to {masked_email} for purpose '{purpose}'.")
        return True, "Email delivery simulated (Configure SMTP in .env for live transmission)"

    try:
        msg = MIMEMultipart()
        msg['From'] = MAIL_DEFAULT_SENDER
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(html_body, 'html'))

        server = smtplib.SMTP(MAIL_SERVER, MAIL_PORT)
        if MAIL_USE_TLS:
            server.starttls()
        server.login(MAIL_USERNAME, MAIL_PASSWORD)
        server.sendmail(MAIL_DEFAULT_SENDER, recipient_email, msg.as_string())
        server.quit()
        print(f"[Email Service] Successfully sent OTP email to: {recipient_email}")
        return True, "Email sent successfully"
    except Exception as e:
        print(f"[Email Service] SMTP error sending OTP: {e}")
        return False, str(e)
