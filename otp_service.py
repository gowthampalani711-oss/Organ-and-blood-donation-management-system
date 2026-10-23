from __future__ import annotations
import os
import re
import secrets
import hashlib
import datetime
from database import DBWrapper
from services.sms_service import send_otp_sms, get_masked_phone, format_10digit_phone
from services.email_service import send_otp_email, send_admin_otp_email

OTP_EXPIRY_SECONDS = 300       # 5 minutes
RESEND_COOLDOWN_SECONDS = 60   # 60 seconds cooldown between resend requests
MAX_VERIFY_ATTEMPTS = 5        # Invalidate after 5 incorrect attempts
OTP_SALT = os.getenv("SECRET_KEY", "lifesaver_organ_blood_donation_secure_otp_salt_2026")


def generate_random_otp() -> str:
    """
    Generates a cryptographically secure random 6-digit OTP code (100000 - 999999).
    Never uses fixed or hardcoded numbers.
    """
    return str(secrets.randbelow(900000) + 100000)


def hash_otp(otp_code: str) -> str:
    """Computes a salted SHA-256 hash for secure storage of the OTP code."""
    payload = f"{str(otp_code).strip()}:{OTP_SALT}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def verify_otp_hash(stored_code_or_hash: str, entered_otp: str) -> bool:
    """Verifies user-entered OTP against the stored SHA-256 hash or legacy plaintext."""
    if not stored_code_or_hash or not entered_otp:
        return False
    # Check SHA-256 salted hash match
    expected_hash = hash_otp(entered_otp)
    if secrets.compare_digest(stored_code_or_hash, expected_hash):
        return True
    # Legacy fallback check (if any old plaintext OTP exists during migration)
    if secrets.compare_digest(stored_code_or_hash, str(entered_otp).strip()):
        return True
    return False


def check_resend_cooldown(phone_or_email: str, purpose: str) -> tuple[bool, int]:
    """
    Checks whether a resend request is being made too quickly within the cooldown window.
    Returns (is_allowed: bool, wait_seconds: int).
    """
    contact_clean = str(phone_or_email).strip().lower(
    ) if "@" in str(phone_or_email) else format_10digit_phone(phone_or_email)
    with DBWrapper() as db:
        latest = db.query_one(
            "SELECT created_at FROM otp_verifications WHERE phone_or_email = %s AND purpose = %s ORDER BY id DESC LIMIT 1",
            (contact_clean, purpose)
        )
        if not latest:
            return True, 0

        created_at = latest.get("created_at")
        if isinstance(created_at, str):
            try:
                created_at = datetime.datetime.strptime(created_at[:19], "%Y-%m-%d %H:%M:%S")
            except Exception:
                created_at = datetime.datetime.now()

        if not created_at:
            return True, 0

        elapsed = (datetime.datetime.now() - created_at).total_seconds()
        if elapsed < RESEND_COOLDOWN_SECONDS:
            return False, int(RESEND_COOLDOWN_SECONDS - elapsed)
        return True, 0


def send_mobile_otp(phone_number: str, purpose: str = "mobile_verification", prerequisite_data: dict = None) -> dict:
    """
    Generates a secure random 6-digit OTP, stores its SHA-256 hash, and dispatches it via SMS.
    Never exposes raw OTPs in responses or browser interfaces.
    """
    phone = format_10digit_phone(phone_number)
    if not phone or len(phone) != 10 or not re.match(r"^[6-9]\d{9}$", phone):
        return {
            "success": False,
            "message_en": "Please enter a valid 10-digit mobile number starting with 6-9.",
            "message_ta": "6-9 இல் தொடங்கும் சரியான 10 இலக்க மொபைல் எண்ணை உள்ளிடவும்."
        }

    # Validate prerequisite data if provided
    if prerequisite_data:
        if "full_name" in prerequisite_data:
            full_name = str(prerequisite_data.get("full_name") or "").strip()
            if not full_name:
                return {
                    "success": False,
                    "message_en": "Full Name is required before requesting OTP.",
                    "message_ta": "OTP கோருவதற்கு முன் முழு பெயர் தேவை."
                }
        if "age" in prerequisite_data and prerequisite_data.get("age") is not None:
            age = str(prerequisite_data.get("age")).strip()
            if not age.isdigit() or int(age) < 18 or int(age) > 100:
                return {
                    "success": False,
                    "message_en": "Valid Age (18+) is required before requesting OTP.",
                    "message_ta": "OTP கோருவதற்கு முன் சரியான வயது (18+) தேவை."
                }
        if "gender" in prerequisite_data:
            gender = str(prerequisite_data.get("gender") or "").strip()
            if not gender:
                return {
                    "success": False,
                    "message_en": "Gender is required before requesting OTP.",
                    "message_ta": "OTP கோருவதற்கு முன் பாலினம் தேர்வு செய்யவும்."
                }

    # Check resend cooldown
    allowed, wait_sec = check_resend_cooldown(phone, purpose)
    if not allowed:
        return {
            "success": False,
            "cooldown_seconds": wait_sec,
            "message_en": f"Please wait {wait_sec} seconds before requesting a new OTP.",
            "message_ta": f"புதிய OTP கோருவதற்கு முன் {wait_sec} வினாடிகள் காத்திருக்கவும்."
        }

    # Generate fresh cryptographically random OTP
    raw_otp_code = generate_random_otp()
    hashed_otp = hash_otp(raw_otp_code)

    now = datetime.datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    expires_at = now + datetime.timedelta(seconds=OTP_EXPIRY_SECONDS)
    expires_str = expires_at.strftime("%Y-%m-%d %H:%M:%S")

    with DBWrapper() as db:
        # Invalidate previous unverified OTPs for this phone & purpose
        db.execute(
            "UPDATE otp_verifications SET is_verified = -1 WHERE phone_or_email = %s AND purpose = %s AND is_verified = 0",
            (phone, purpose)
        )
        # Store hashed OTP
        db.execute(
            """INSERT INTO otp_verifications (phone_or_email, otp_code, purpose, attempts, max_attempts, expires_at, is_verified, created_at)
               VALUES (%s, %s, %s, 0, %s, %s, 0, %s)""",
            (phone, hashed_otp, purpose, MAX_VERIFY_ATTEMPTS, expires_str, now_str)
        )

    # Dispatch via live SMS gateway
    sms_sent, sms_status_msg = send_otp_sms(phone, raw_otp_code, purpose)

    if not sms_sent:
        return {
            "success": False,
            "message_en": sms_status_msg or "Unable to deliver OTP via SMS. Please check SMS gateway configuration.",
            "message_ta": "OTP அனுப்ப முடியவில்லை. உங்கள் மொபைல் எண் மற்றும் SMS அமைப்புகளை சரிபார்க்கவும்.",
            "error_detail": sms_status_msg
        }

    return {
        "success": True,
        "message_en": "OTP has been sent to your mobile number.",
        "message_ta": "உங்கள் மொபைல் எண்ணிற்கு OTP அனுப்பப்பட்டது.",
        "masked_phone": get_masked_phone(phone),
        "expires_in_seconds": OTP_EXPIRY_SECONDS,
        "cooldown_seconds": RESEND_COOLDOWN_SECONDS
    }


def verify_mobile_otp(phone_number: str, entered_otp: str, purpose: str = "mobile_verification") -> dict:
    """
    Verifies user-entered SMS OTP against the stored SHA-256 hash.
    Enforces 5-minute expiry and max 5 attempts limit.
    """
    phone = format_10digit_phone(phone_number)
    entered_otp = str(entered_otp or "").strip()

    if not entered_otp or len(entered_otp) != 6 or not entered_otp.isdigit():
        return {
            "success": False,
            "message_en": "Please enter a valid 6-digit OTP code.",
            "message_ta": "சரியான 6 இலக்க OTP குறியீட்டை உள்ளிடவும்."
        }

    with DBWrapper() as db:
        record = db.query_one(
            "SELECT * FROM otp_verifications WHERE phone_or_email = %s AND purpose = %s AND is_verified = 0 ORDER BY id DESC LIMIT 1",
            (phone, purpose)
        )

        if not record:
            return {
                "success": False,
                "message_en": "No active OTP request found. Please request a new OTP.",
                "message_ta": "செயலில் உள்ள OTP கோரிக்கை எதுவும் இல்லை. புதிய OTP கோரவும்."
            }

        rec_id = record["id"]
        attempts = int(record.get("attempts", 0) or 0)
        max_attempts = int(record.get("max_attempts", MAX_VERIFY_ATTEMPTS) or MAX_VERIFY_ATTEMPTS)

        # Check maximum attempts
        if attempts >= max_attempts:
            db.execute("UPDATE otp_verifications SET is_verified = -1 WHERE id = %s", (rec_id,))
            return {
                "success": False,
                "message_en": "Maximum verification attempts exceeded. Please request a new OTP.",
                "message_ta": "அதிகபட்ச முயற்சிகள் கடந்துவிட்டன. புதிய OTP கோரவும்."
            }

        # Check expiry
        now = datetime.datetime.now()
        expires_at = record["expires_at"]
        if isinstance(expires_at, str):
            try:
                expires_at = datetime.datetime.strptime(expires_at[:19], "%Y-%m-%d %H:%M:%S")
            except Exception:
                expires_at = now + datetime.timedelta(minutes=1)

        if now > expires_at:
            db.execute("UPDATE otp_verifications SET is_verified = -1 WHERE id = %s", (rec_id,))
            return {
                "success": False,
                "message_en": "OTP has expired. Please request a new OTP.",
                "message_ta": "OTP காலாவதியாகிவிட்டது. புதிய OTP கோரவும்."
            }

        # Verify Hash
        stored_code = record["otp_code"]
        is_valid = verify_otp_hash(stored_code, entered_otp)

        if not is_valid:
            new_attempts = attempts + 1
            if new_attempts >= max_attempts:
                db.execute("UPDATE otp_verifications SET attempts = %s, is_verified = -1 WHERE id = %s",
                           (new_attempts, rec_id))
                return {
                    "success": False,
                    "message_en": "Incorrect OTP. Maximum attempts reached. Please request a new OTP.",
                    "message_ta": "தவறான OTP. அதிகபட்ச வரம்பு முடிந்தது. புதிய OTP கோரவும்."
                }
            else:
                db.execute("UPDATE otp_verifications SET attempts = %s WHERE id = %s", (new_attempts, rec_id))
                remaining = max_attempts - new_attempts
                return {
                    "success": False,
                    "message_en": f"Invalid OTP. {remaining} attempt(s) remaining.",
                    "message_ta": f"தவறான OTP. மேலும் {remaining} முயற்சி(கள்) உள்ளன."
                }

        # Mark as verified
        db.execute("UPDATE otp_verifications SET is_verified = 1 WHERE id = %s", (rec_id,))

    return {
        "success": True,
        "message_en": "Mobile number verified successfully!",
        "message_ta": "மொபைல் எண் வெற்றிகரமாக சரிபார்க்கப்பட்டது!"
    }


def get_masked_email(email_str: str) -> str:
    """Masks an email address for secure UI display (e.g. ad****@hospital.org)."""
    email = str(email_str or "").strip().lower()
    if "@" not in email:
        return email
    user_part, domain_part = email.split("@", 1)
    if len(user_part) <= 2:
        masked_user = user_part[0] + "****" if user_part else "****"
    else:
        masked_user = user_part[:2] + "****"
    return f"{masked_user}@{domain_part}"


def send_email_otp(email_address: str, purpose: str = "email_verification", prerequisite_data: dict = None) -> dict:
    """
    Generates a secure random 6-digit OTP and dispatches it to the entered email address.
    """
    email = str(email_address).strip().lower()
    if not email or not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return {
            "success": False,
            "message_en": "Please enter a valid email address.",
            "message_ta": "சரியான மின்னஞ்சல் முகவரியை உள்ளிடவும்."
        }

    # Check resend cooldown
    allowed, wait_sec = check_resend_cooldown(email, purpose)
    if not allowed:
        return {
            "success": False,
            "cooldown_seconds": wait_sec,
            "message_en": f"Please wait {wait_sec} seconds before requesting a new OTP.",
            "message_ta": f"புதிய OTP கோருவதற்கு முன் {wait_sec} வினாடிகள் காத்திருக்கவும்."
        }

    # Generate fresh random OTP
    raw_otp_code = generate_random_otp()
    hashed_otp = hash_otp(raw_otp_code)

    now = datetime.datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    expires_at = now + datetime.timedelta(seconds=OTP_EXPIRY_SECONDS)
    expires_str = expires_at.strftime("%Y-%m-%d %H:%M:%S")

    with DBWrapper() as db:
        db.execute(
            "UPDATE otp_verifications SET is_verified = -1 WHERE phone_or_email = %s AND purpose = %s AND is_verified = 0",
            (email, purpose)
        )
        db.execute(
            """INSERT INTO otp_verifications (phone_or_email, otp_code, purpose, attempts, max_attempts, expires_at, is_verified, created_at)
               VALUES (%s, %s, %s, 0, %s, %s, 0, %s)""",
            (email, hashed_otp, purpose, MAX_VERIFY_ATTEMPTS, expires_str, now_str)
        )

    # Dispatch via Email Service
    if purpose.startswith("admin"):
        send_admin_otp_email(email, raw_otp_code, purpose)
    else:
        send_otp_email(email, raw_otp_code, purpose)

    return {
        "success": True,
        "message_en": "OTP has been sent to your registered email address.",
        "message_ta": "உங்கள் மின்னஞ்சல் முகவரிக்கு OTP வெற்றிகரமாக அனுப்பப்பட்டது.",
        "masked_email": get_masked_email(email),
        "expires_in_seconds": OTP_EXPIRY_SECONDS,
        "cooldown_seconds": RESEND_COOLDOWN_SECONDS
    }


def verify_email_otp(email_address: str, entered_otp: str, purpose: str = "email_verification") -> dict:
    """
    Verifies the user-entered Email OTP against the stored SHA-256 hash.
    """
    email = str(email_address).strip().lower()
    entered_otp = str(entered_otp or "").strip()

    if not entered_otp or len(entered_otp) != 6 or not entered_otp.isdigit():
        return {
            "success": False,
            "message_en": "Please enter a valid 6-digit OTP code.",
            "message_ta": "சரியான 6 இலக்க OTP குறியீட்டை உள்ளிடவும்."
        }

    with DBWrapper() as db:
        record = db.query_one(
            "SELECT * FROM otp_verifications WHERE phone_or_email = %s AND purpose = %s AND is_verified = 0 ORDER BY id DESC LIMIT 1",
            (email, purpose)
        )

        if not record:
            return {
                "success": False,
                "message_en": "No active OTP request found. Please request a new OTP.",
                "message_ta": "செயலில் உள்ள OTP கோரிக்கை எதுவும் இல்லை. புதிய OTP கோரவும்."
            }

        rec_id = record["id"]
        attempts = int(record.get("attempts", 0) or 0)
        max_attempts = int(record.get("max_attempts", MAX_VERIFY_ATTEMPTS) or MAX_VERIFY_ATTEMPTS)

        if attempts >= max_attempts:
            db.execute("UPDATE otp_verifications SET is_verified = -1 WHERE id = %s", (rec_id,))
            return {
                "success": False,
                "message_en": "Maximum verification attempts exceeded. Please request a new OTP.",
                "message_ta": "அதிகபட்ச முயற்சிகள் கடந்துவிட்டன. புதிய OTP கோரவும்."
            }

        now = datetime.datetime.now()
        expires_at = record["expires_at"]
        if isinstance(expires_at, str):
            try:
                expires_at = datetime.datetime.strptime(expires_at[:19], "%Y-%m-%d %H:%M:%S")
            except Exception:
                expires_at = now + datetime.timedelta(minutes=1)

        if now > expires_at:
            db.execute("UPDATE otp_verifications SET is_verified = -1 WHERE id = %s", (rec_id,))
            return {
                "success": False,
                "message_en": "OTP has expired. Please request a new OTP.",
                "message_ta": "OTP காலாவதியாகிவிட்டது. புதிய OTP கோரவும்."
            }

        stored_code = record["otp_code"]
        is_valid = verify_otp_hash(stored_code, entered_otp)

        if not is_valid:
            new_attempts = attempts + 1
            if new_attempts >= max_attempts:
                db.execute("UPDATE otp_verifications SET attempts = %s, is_verified = -1 WHERE id = %s",
                           (new_attempts, rec_id))
                return {
                    "success": False,
                    "message_en": "Incorrect OTP. Maximum attempts reached. Please request a new OTP.",
                    "message_ta": "தவறான OTP. அதிகபட்ச வரம்பு முடிந்தது. புதிய OTP கோரவும்."
                }
            else:
                db.execute("UPDATE otp_verifications SET attempts = %s WHERE id = %s", (new_attempts, rec_id))
                remaining = max_attempts - new_attempts
                return {
                    "success": False,
                    "message_en": f"Invalid OTP. {remaining} attempt(s) remaining.",
                    "message_ta": f"தவறான OTP. மேலும் {remaining} முயற்சி(கள்) உள்ளன."
                }

        db.execute("UPDATE otp_verifications SET is_verified = 1 WHERE id = %s", (rec_id,))

    return {
        "success": True,
        "message_en": "Email address verified successfully!",
        "message_ta": "மின்னஞ்சல் முகவரி வெற்றிகரமாக சரிபார்க்கப்பட்டது!"
    }


def send_registration_otp(phone_or_email: str, purpose: str = "donor_registration",
                          prerequisite_data: dict = None) -> dict:
    """
    Unified router for mobile or email OTP dispatch.
    """
    contact = str(phone_or_email).strip()
    if "@" in contact:
        return send_email_otp(contact, purpose, prerequisite_data)
    else:
        return send_mobile_otp(contact, purpose, prerequisite_data)


def verify_registration_otp(phone_or_email: str, entered_otp: str, purpose: str = "donor_registration") -> dict:
    """
    Unified router for mobile or email OTP verification.
    """
    contact = str(phone_or_email).strip()
    if "@" in contact:
        return verify_email_otp(contact, entered_otp, purpose)
    else:
        return verify_mobile_otp(contact, entered_otp, purpose)


def is_contact_verified(phone_or_email: str, purpose: str = "donor_registration", max_age_minutes: int = 60) -> bool:
    """
    Checks if a phone number or email address has been successfully verified recently.
    """
    contact = str(phone_or_email).strip().lower(
    ) if "@" in str(phone_or_email) else format_10digit_phone(phone_or_email)
    with DBWrapper() as db:
        record = db.query_one(
            "SELECT * FROM otp_verifications WHERE phone_or_email = %s AND purpose = %s AND is_verified = 1 ORDER BY id DESC LIMIT 1",
            (contact, purpose)
        )
        if not record:
            return False

        created_at = record.get("created_at")
        if isinstance(created_at, str):
            try:
                created_at = datetime.datetime.strptime(created_at[:19], "%Y-%m-%d %H:%M:%S")
            except Exception:
                created_at = datetime.datetime.now()

        if created_at:
            age_min = (datetime.datetime.now() - created_at).total_seconds() / 60.0
            if age_min > max_age_minutes:
                return False

        return True
