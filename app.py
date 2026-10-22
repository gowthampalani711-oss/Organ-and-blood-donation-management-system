import os
import re
import uuid
import datetime
import random
import hashlib
import hmac
from flask import Flask, request, jsonify, render_template, session, redirect
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from dotenv import load_dotenv

from database import DBWrapper, init_database
from services.sms_service import format_10digit_phone
from services.otp_service import (
    send_mobile_otp,
    verify_mobile_otp,
    send_email_otp,
    verify_email_otp,
    send_registration_otp,
    verify_registration_otp,
    get_masked_email
)
from services.matching import match_organ_donors, match_blood_donors
from services.qr_service import generate_donor_qr
from services.pdf_generator import generate_donor_card_pdf
from services.email_service import send_donor_card_email

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
ENV_FILE_PATH = os.path.join(PROJECT_ROOT, ".env")
if os.path.exists(ENV_FILE_PATH):
    load_dotenv(dotenv_path=ENV_FILE_PATH)
else:
    load_dotenv()

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.getenv("SECRET_KEY", "life_saver_odms_super_secret_key_2026")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max upload

ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
ALLOWED_REPORT_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}


def allowed_file(filename, allowed_set):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_set


def safe_check_password_hash(pwhash: str, password: str) -> bool:
    """Safely verifies password hash across all Werkzeug and Python versions, supporting scrypt and pbkdf2."""
    if not pwhash or not password:
        return False
    if pwhash.startswith("scrypt:"):
        try:
            method, salt, hashval = pwhash.split("$", 2)
            method_parts = method.split(":")
            if method_parts[0] == "scrypt":
                if len(method_parts) >= 4:
                    n, r, p = map(int, method_parts[1:4])
                else:
                    n, r, p = 32768, 8, 1
                maxmem = 132 * n * r * p
                derived = hashlib.scrypt(
                    password.encode("utf-8"),
                    salt=salt.encode("utf-8"),
                    n=n, r=r, p=p,
                    maxmem=maxmem
                ).hex()
                return hmac.compare_digest(derived, hashval)
        except Exception as e:
            print(f"[Auth] scrypt verification exception: {e}")
    try:
        return check_password_hash(pwhash, password)
    except Exception as e:
        print(f"[Auth] check_password_hash exception: {e}")
        return False


# Initialize Database on app startup
with app.app_context():
    init_database()

# ==========================================================
# PAGE ROUTES
# ==========================================================


@app.route("/")
def index():
    return render_template("index.html")


@app.after_request
def add_admin_cache_control(response):
    """Prevent aggressive caching so browser always loads updated templates, styles and scripts."""
    if request.path.startswith("/admin") or request.path.startswith("/api/admin") or request.path.startswith("/static") or request.path == "/":
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# Admin UI separate page routes


@app.route("/admin")
@app.route("/admin/")
def admin_overview():
    if not session.get("admin_id"):
        return redirect("/admin/signin")
    return render_template("index.html")


@app.route("/admin/signin")
def admin_signin_page():
    if session.get("admin_id"):
        return redirect("/admin")
    return render_template("admin_signin.html")


@app.route("/admin/login")
def admin_login_page():
    return redirect("/admin/signin")


@app.route("/admin/signup")
def admin_signup_page():
    if session.get("admin_id"):
        return redirect("/admin")
    return render_template("admin_signup.html")


@app.route("/admin/forgot-password")
def admin_forgot_password_page():
    if session.get("admin_id"):
        return redirect("/admin")
    return render_template("admin_forgot_password.html")


@app.route("/admin/logout", methods=["GET", "POST"])
def admin_logout():
    """Clear admin session completely and redirect to main public home page."""
    session.clear()
    return redirect("/")


@app.route("/admin/donors")
def admin_donors_page():
    if not session.get("admin_id"):
        return redirect("/admin/signin")
    return render_template("admin_donors.html")


@app.route("/admin/organ-donors")
def admin_organ_donors_page():
    if not session.get("admin_id"):
        return redirect("/admin/signin")
    return render_template("index.html")


@app.route("/admin/blood-donors")
def admin_blood_donors_page():
    if not session.get("admin_id"):
        return redirect("/admin/signin")
    return render_template("admin_blood_donors.html")


@app.route("/admin/find-organ")
def admin_find_organ_page():
    if not session.get("admin_id"):
        return redirect("/admin/signin")
    return render_template("admin_find_organ.html")


@app.route("/admin/blood-requests")
def admin_blood_requests_page():
    if not session.get("admin_id"):
        return redirect("/admin/signin")
    return render_template("admin_blood_requests.html")


@app.route("/admin/receivers")
def admin_receivers_page():
    if not session.get("admin_id"):
        return redirect("/admin/signin")
    return render_template("admin_receivers.html")


@app.route("/admin/search-match")
def admin_search_match_page():
    if not session.get("admin_id"):
        return redirect("/admin/signin")
    return render_template("index.html")


@app.route("/admin/records")
@app.route("/admin/pending-records")
@app.route("/admin/approved-records")
@app.route("/admin/rejected-records")
def admin_records_page():
    if not session.get("admin_id"):
        return redirect("/admin/signin")
    return render_template("admin_records.html")


@app.route("/verify-donor/<donor_id>")
def verify_donor(donor_id):
    """Public verification page when QR code on Donor Card is scanned."""
    with DBWrapper() as db:
        donor = db.query_one(
            "SELECT donor_id, full_name, blood_group, organ_type, city, status, created_at FROM donors WHERE donor_id = %s",
            (donor_id,
             ))
    return render_template("verify_donor.html", donor=donor)

# ==========================================================
# OTP API ENDPOINTS (Mobile SMS & Email Separate Flows)
# ==========================================================


@app.route("/send-mobile-otp", methods=["POST"])
@app.route("/api/otp/send-mobile", methods=["POST"])
def api_send_mobile_otp():
    data = request.get_json(silent=True) or request.form or {}
    phone = str(data.get("phone") or data.get("phone_or_email") or "").strip()
    purpose = str(data.get("purpose", "mobile_verification")).strip()
    prerequisite_data = data.get("prerequisite_data")

    if not phone:
        return jsonify({"success": False, "message_en": "Mobile number is required.",
                       "message_ta": "தொலைபேசி எண் அவசியம்."}), 400

    res = send_mobile_otp(phone, purpose, prerequisite_data)
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code


@app.route("/verify-mobile-otp", methods=["POST"])
@app.route("/api/otp/verify-mobile", methods=["POST"])
def api_verify_mobile_otp():
    data = request.get_json(silent=True) or request.form or {}
    phone = str(data.get("phone") or data.get("phone_or_email") or "").strip()
    otp_code = str(data.get("otp") or data.get("otp_code") or "").strip()
    purpose = str(data.get("purpose", "mobile_verification")).strip()

    if not phone or not otp_code:
        return jsonify({"success": False, "message_en": "Mobile number and 6-digit OTP code are required.",
                       "message_ta": "தொலைபேசி எண் மற்றும் 6 இலக்க OTP குறியீடு அவசியம்."}), 400

    res = verify_mobile_otp(phone, otp_code, purpose)
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code


@app.route("/send-email-otp", methods=["POST"])
@app.route("/api/otp/send-email", methods=["POST"])
def api_send_email_otp():
    data = request.get_json(silent=True) or request.form or {}
    email = str(data.get("email") or data.get("phone_or_email") or "").strip().lower()
    purpose = str(data.get("purpose", "email_verification")).strip()
    prerequisite_data = data.get("prerequisite_data")

    if not email:
        return jsonify({"success": False, "message_en": "Email address is required.",
                       "message_ta": "மின்னஞ்சல் முகவரி அவசியம்."}), 400

    res = send_email_otp(email, purpose, prerequisite_data)
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code


@app.route("/verify-email-otp", methods=["POST"])
@app.route("/api/otp/verify-email", methods=["POST"])
def api_verify_email_otp():
    data = request.get_json(silent=True) or request.form or {}
    email = str(data.get("email") or data.get("phone_or_email") or "").strip().lower()
    otp_code = str(data.get("otp") or data.get("otp_code") or "").strip()
    purpose = str(data.get("purpose", "email_verification")).strip()

    if not email or not otp_code:
        return jsonify({"success": False, "message_en": "Email address and 6-digit OTP code are required.",
                       "message_ta": "மின்னஞ்சல் முகவரி மற்றும் 6 இலக்க OTP குறியீடு அவசியம்."}), 400

    res = verify_email_otp(email, otp_code, purpose)
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code


@app.route("/api/otp/send", methods=["POST"])
def api_otp_send():
    data = request.get_json(silent=True) or request.form or {}
    phone_or_email = str(data.get("phone_or_email") or data.get("phone") or data.get("email") or "").strip()
    password = str(data.get("password", request.form.get("password", ""))).strip()
    purpose = str(data.get("purpose", "donor_registration")).strip()
    prerequisite_data = data.get("prerequisite_data")

    # Admin Signup OTP Flow: Sent via Email to the entered email address
    if purpose == "admin_signup":
        email = str(data.get("email") or phone_or_email).strip().lower()
        if not email or not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return jsonify({"success": False, "message_en": "Please enter a valid email address.",
                           "message_ta": "சரியான மின்னஞ்சல் முகவரியை உள்ளிடவும்."}), 400

        with DBWrapper() as db:
            existing = db.query_one("SELECT id FROM admins WHERE LOWER(TRIM(email)) = %s", (email,))
            if existing:
                return jsonify({"success": False, "message_en": "An admin account with this email address already exists.",
                               "message_ta": "இந்த மின்னஞ்சல் முகவரியுடன் ஒரு நிர்வாகக் கணக்கு ஏற்கனவே உள்ளது."}), 409

        res = send_email_otp(email, "admin_signup", prerequisite_data)
        status_code = 200 if res.get("success") else 400
        return jsonify(res), status_code

    # Admin Login OTP Flow: Credentials check first, then Email OTP to admin's registered email
    if purpose == "admin_login":
        identifier = phone_or_email.strip().lower()
        if not identifier or not password:
            return jsonify({"success": False, "message_en": "Email and password are required.",
                           "message_ta": "மின்னஞ்சல் மற்றும் கடவுச்சொல் அவசியம்."}), 400

        with DBWrapper() as db:
            admin = db.query_one(
                "SELECT * FROM admins WHERE LOWER(TRIM(email)) = %s OR LOWER(TRIM(username)) = %s",
                (identifier, identifier)
            )
        if not admin:
            return jsonify({"success": False, "message_en": "No admin account found with this email. Please sign up first.",
                           "message_ta": "இந்த மின்னஞ்சலில் நிர்வாகக் கணக்கு எதுவும் கிடைக்கவில்லை. முதலில் பதிவு செய்யவும்."}), 401

        if not safe_check_password_hash(admin["password_hash"], password):
            return jsonify({"success": False, "message_en": "Incorrect password. Please try again.",
                           "message_ta": "தவறான கடவுச்சொல். மீண்டும் முயற்சிக்கவும்."}), 401

        admin_email = admin["email"]
        res = send_email_otp(admin_email, "admin_login")
        if res.get("success"):
            res["masked_email"] = get_masked_email(admin_email)
            res["requires_otp"] = True
            res["admin_email"] = admin_email
        status_code = 200 if res.get("success") else 400
        return jsonify(res), status_code

    # Admin Forgot Password OTP Flow: Sent via Email
    if purpose == "admin_reset_password":
        identifier = phone_or_email.strip().lower()
        with DBWrapper() as db:
            admin = db.query_one(
                "SELECT * FROM admins WHERE LOWER(TRIM(email)) = %s OR LOWER(TRIM(username)) = %s",
                (identifier, identifier)
            )
        if not admin:
            return jsonify({"success": False, "message_en": "No admin account found with this email. Please sign up first.",
                           "message_ta": "இந்த மின்னஞ்சலில் நிர்வாகக் கணக்கு எதுவும் கிடைக்கவில்லை."}), 404

        admin_email = admin["email"]
        res = send_email_otp(admin_email, "admin_reset_password")
        if res.get("success"):
            res["masked_email"] = get_masked_email(admin_email)
        status_code = 200 if res.get("success") else 400
        return jsonify(res), status_code

    # Donor / Generic Registration OTP Flow
    if not phone_or_email:
        return jsonify({"success": False, "message_en": "Mobile number is required.",
                       "message_ta": "மொபைல் எண் அவசியம்."}), 400

    res = send_registration_otp(phone_or_email, purpose, prerequisite_data)
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code


@app.route("/api/otp/verify", methods=["POST"])
def api_otp_verify():
    data = request.get_json(silent=True) or request.form or {}
    phone_or_email = str(data.get("phone_or_email") or data.get("phone") or data.get("email") or "").strip()
    otp_code = str(data.get("otp_code") or data.get("otp") or "").strip()
    purpose = str(data.get("purpose", "donor_registration")).strip()

    if not phone_or_email or not otp_code:
        return jsonify({"success": False, "message_en": "Email/phone and 6-digit OTP code are required.",
                       "message_ta": "மின்னஞ்சல்/மொபைல் எண் மற்றும் 6 இலக்க OTP குறியீடு அவசியம்."}), 400

    if purpose in ("admin_login", "admin_signup", "admin_reset_password"):
        target_email = phone_or_email.lower()
        if "@" not in target_email:
            with DBWrapper() as db:
                admin = db.query_one(
                    "SELECT email FROM admins WHERE LOWER(TRIM(username)) = %s",
                    (target_email,)
                )
                if admin and admin.get("email"):
                    target_email = admin["email"]
        res = verify_email_otp(target_email, otp_code, purpose)
        status_code = 200 if res.get("success") else 400
        return jsonify(res), status_code

    res = verify_registration_otp(phone_or_email, otp_code, purpose)
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code

# ==========================================================
# DONOR REGISTRATION (Requirement #2, #4, #20)
# ==========================================================


@app.route("/api/donors/register", methods=["POST"])
def api_donor_register():
    full_name = request.form.get("full_name", "").strip()
    age = request.form.get("age", "").strip()
    gender = request.form.get("gender", "").strip()
    raw_phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip().lower()
    blood_group = request.form.get("blood_group", "").strip()
    organ_type = request.form.get("organ_type", "").strip()
    address = request.form.get("address", "").strip()
    city = request.form.get("city", "").strip()
    medical_history = request.form.get("medical_history", "").strip()
    availability_status = request.form.get("availability_status", "Available").strip() or "Available"

    # Default gender if omitted
    if not gender:
        gender = "Male"

    # 1. Validate All Required Fields
    if not full_name or len(full_name) < 2:
        return jsonify({"success": False, "message": "Please provide a valid full name."}), 400

    if not age or not age.isdigit() or int(age) < 18 or int(age) > 100:
        return jsonify({"success": False, "message": "Age must be between 18 and 100."}), 400

    if gender not in ("Male", "Female", "Other"):
        return jsonify({"success": False, "message": "Please select a valid gender (Male, Female, or Other)."}), 400

    # 2. Validate Phone Number (clean non-digits, extract 10-digit number starting with 6-9)
    clean_phone = re.sub(r"\D", "", raw_phone)
    if len(clean_phone) == 12 and clean_phone.startswith("91"):
        clean_phone = clean_phone[2:]
    elif len(clean_phone) > 10:
        clean_phone = clean_phone[-10:]

    if not clean_phone or not re.match(r"^[6-9]\d{9}$", clean_phone):
        return jsonify({
            "success": False,
            "message": "Invalid phone number format. Please provide a valid 10-digit mobile number starting with 6, 7, 8, or 9."
        }), 400

    phone = clean_phone

    if not email or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return jsonify({"success": False, "message": "Please provide a valid email address."}), 400

    valid_blood_groups = ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-')
    if blood_group not in valid_blood_groups:
        return jsonify({"success": False, "message": "Please select a valid blood group."}), 400

    if not organ_type:
        return jsonify({"success": False, "message": "Please select at least one organ to pledge."}), 400

    if not address or len(address) < 3:
        return jsonify({"success": False, "message": "Please provide your full street address."}), 400

    if not city or len(city) < 2:
        return jsonify({"success": False, "message": "Please provide your city or district."}), 400

    # 3. Check Duplicate Donor in MySQL
    with DBWrapper() as db:
        existing_phone = db.query_one("SELECT donor_id, phone FROM donors WHERE phone = %s", (phone,))
        if existing_phone:
            return jsonify({
                "success": False,
                "message": f"A donor with phone number {phone} is already registered (Donor ID: {existing_phone['donor_id']}). Duplicate registration is not permitted."
            }), 400

        existing_email = db.query_one("SELECT donor_id, email FROM donors WHERE LOWER(TRIM(email)) = %s", (email,))
        if existing_email:
            return jsonify({
                "success": False,
                "message": f"A donor with email address {email} is already registered (Donor ID: {existing_email['donor_id']}). Duplicate registration is not permitted."
            }), 400

    # 4. Generate Unique Donor ID (ODMS-ORG-YYYY-XXXX) with verified database uniqueness
    current_year = datetime.datetime.now().year
    with DBWrapper() as db:
        while True:
            candidate_id = f"ODMS-ORG-{current_year}-{random.randint(1000, 9999)}"
            exists = db.query_one("SELECT id FROM donors WHERE donor_id = %s", (candidate_id,))
            if not exists:
                donor_id = candidate_id
                break

    # 5. Handle Donor Photo Upload if provided
    photo_url = "/static/img/default-avatar.png"
    if "photo" in request.files:
        photo_file = request.files["photo"]
        if photo_file and photo_file.filename and allowed_file(photo_file.filename, ALLOWED_IMAGE_EXTENSIONS):
            filename = f"donor_{donor_id}_{secure_filename(photo_file.filename)}"
            upload_dir = os.path.join(app.static_folder, "uploads", "photos")
            os.makedirs(upload_dir, exist_ok=True)
            save_path = os.path.join(upload_dir, filename)
            photo_file.save(save_path)
            photo_url = f"/static/uploads/photos/{filename}"

    # 6. Generate QR Code
    qr_web_url, _ = generate_donor_qr(donor_id)

    # 7. Generate Donor Card PDF
    donor_dict = {
        "donor_id": donor_id,
        "full_name": full_name,
        "blood_group": blood_group,
        "organ_type": organ_type,
        "city": city,
        "status": "Approved",
        "photo_url": photo_url,
        "email": email,
        "phone": phone,
        "created_at": datetime.datetime.now().strftime("%d-%b-%Y")
    }
    pdf_web_url, pdf_abs_path = generate_donor_card_pdf(donor_dict)

    # 8. Save Donor Details into MySQL
    with DBWrapper() as db:
        db.execute(
            """INSERT INTO donors (donor_id, full_name, age, gender, phone, email, blood_group, organ_type, address, city, medical_history, availability_status, photo_url, qr_code_url, pdf_url, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Approved')""",
            (donor_id, full_name, int(age), gender, phone, email, blood_group, organ_type, address,
             city, medical_history, availability_status, photo_url, qr_web_url, pdf_web_url)
        )
        # Add system notification
        db.execute(
            """INSERT INTO notifications (user_type, user_identifier, title_en, title_ta, message_en, message_ta, type)
               VALUES ('admin', NULL, %s, %s, %s, %s, 'success')""",
            (
                f"New Organ Donor Registered: {full_name} ({donor_id})",
                f"புதிய உறுப்பு தானமளிப்பவர் பதிவு: {full_name} ({donor_id})",
                f"Donor {full_name} ({donor_id}) pledged {organ_type} in {city}.",
                f"{full_name} ({donor_id}) {city} மாவட்டத்தில் {organ_type} உறுப்பு தான உறுதிமொழி செய்துள்ளார்.",
            )
        )

    # 9. Send Donor Card PDF Automatically to Email
    email_sent, email_status = send_donor_card_email(email, full_name, donor_id, pdf_abs_path)

    donor_dict["qr_code_url"] = qr_web_url
    donor_dict["pdf_url"] = pdf_web_url
    donor_dict["email_sent"] = email_sent

    # 10. Prepare Clear Response Message
    if email_sent:
        response_msg = "Donor Registration Successful! Your Donor Card has been sent to your registered email address."
    else:
        response_msg = f"Donor Registration Successful! Donor ID: {donor_id}. Note: Email delivery could not be completed ({email_status}). You can download your Donor Card below."

    return jsonify({
        "success": True,
        "message": response_msg,
        "donor_id": donor_id,
        "donor": donor_dict,
        "email_sent": email_sent
    })


@app.route("/api/donors/<donor_id>/resend-card", methods=["POST"])
def api_resend_donor_card(donor_id):
    with DBWrapper() as db:
        donor = db.query_one("SELECT * FROM donors WHERE donor_id = %s", (donor_id,))
        if not donor:
            return jsonify({"success": False, "message": "Donor record not found."}), 404

        pdf_path = os.path.join(app.static_folder, "uploads", "cards", f"donor_card_{donor_id}.pdf")
        if not os.path.exists(pdf_path):
            donor_dict = {
                "donor_id": donor["donor_id"],
                "full_name": donor["full_name"],
                "blood_group": donor["blood_group"],
                "organ_type": donor["organ_type"],
                "city": donor["city"],
                "status": donor.get("status", "Approved"),
                "photo_url": donor.get("photo_url", ""),
                "email": donor["email"],
                "created_at": donor.get("created_at")
            }
            _, pdf_path = generate_donor_card_pdf(donor_dict)

        email_sent, email_msg = send_donor_card_email(
            donor["email"], donor["full_name"], donor["donor_id"], pdf_path
        )
        if email_sent:
            return jsonify({"success": True, "message": f"Donor Card PDF resent successfully to {donor['email']}."})
        else:
            return jsonify({"success": False, "message": f"Email delivery failed: {email_msg}"}), 500

# ==========================================================
# BLOOD DONOR REGISTRATION (Requirement #7)
# ==========================================================


@app.route("/api/blood-donors/register", methods=["POST"])
def api_blood_donor_register():
    full_name = request.form.get("full_name", "").strip()
    age = request.form.get("age", "").strip()
    gender = request.form.get("gender", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip().lower()
    blood_group = request.form.get("blood_group", "").strip()
    last_donation_date = request.form.get("last_donation_date") or None
    address = request.form.get("address", "").strip()
    city = request.form.get("city", "").strip()
    availability_status = request.form.get("availability_status", "Available")

    if not all([full_name, age, gender, phone, email, blood_group, address, city]):
        return jsonify({"success": False, "message": "All required fields must be completed."}), 400

    if not re.match(r"^[6-9]\d{9}$", phone):
        return jsonify({"success": False, "message": "Invalid 10-digit mobile number."}), 400

    if not age.isdigit() or int(age) < 18 or int(age) > 65:
        return jsonify({"success": False, "message": "Blood donors must be between 18 and 65 years old."}), 400

    with DBWrapper() as db:
        existing = db.query_one("SELECT id FROM blood_donors WHERE phone = %s OR email = %s", (phone, email))
        if existing:
            return jsonify(
                {"success": False, "message": "A blood donor with this phone number or email is already registered."}), 400

        blood_donor_id = f"ODMS-BLD-{datetime.datetime.now().year}-{random.randint(1000, 9999)}"

        # Handle Donor Photo Upload if provided
        photo_url = "/static/img/default-avatar.png"
        if "photo" in request.files:
            photo_file = request.files["photo"]
            if photo_file and photo_file.filename and allowed_file(photo_file.filename, ALLOWED_IMAGE_EXTENSIONS):
                filename = f"blood_donor_{blood_donor_id}_{secure_filename(photo_file.filename)}"
                upload_dir = os.path.join(app.static_folder, "uploads", "photos")
                os.makedirs(upload_dir, exist_ok=True)
                save_path = os.path.join(upload_dir, filename)
                photo_file.save(save_path)
                photo_url = f"/static/uploads/photos/{filename}"

        db.execute(
            """INSERT INTO blood_donors (blood_donor_id, full_name, age, gender, phone, email, blood_group, last_donation_date, address, city, availability_status, photo_url, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Pending')""",
            (blood_donor_id, full_name, int(age), gender, phone, email,
             blood_group, last_donation_date, address, city, availability_status, photo_url)
        )

        db.execute(
            """INSERT INTO notifications (user_type, user_identifier, title_en, title_ta, message_en, message_ta, type)
               VALUES ('admin', NULL, %s, %s, %s, %s, 'info')""",
            (
                f"New Blood Donor: {full_name} ({blood_group})",
                f"புதிய ரத்த தானமளிப்பவர்: {full_name} ({blood_group})",
                f"{full_name} registered as {blood_group} blood donor in {city}.",
                f"{full_name} {city} மாவட்டத்தில் {blood_group} ரத்த தானமளிப்பவராகப் பதிவு செய்துள்ளார்."
            )
        )

    return jsonify({
        "success": True,
        "message": "Blood donor registered successfully!",
        "blood_donor_id": blood_donor_id
    })

# ==========================================================
# RECEIVER REGISTRATION & HEALTH REPORTS (Requirement #5)
# ==========================================================


@app.route("/api/receivers/register", methods=["POST"])
def api_receiver_register():
    name = request.form.get("name", "").strip()
    age = request.form.get("age", "").strip()
    gender = request.form.get("gender", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip().lower()
    blood_group = request.form.get("blood_group", "").strip()
    needed_organ = request.form.get("needed_organ", "").strip()
    address = request.form.get("address", "").strip()
    city = request.form.get("city", "").strip()
    emergency_level = request.form.get("emergency_level", "High")
    contact_number = request.form.get("contact_number", "").strip()

    if not all([name, age, gender, phone, email, blood_group, needed_organ, address, city, contact_number]):
        return jsonify({"success": False, "message": "Please fill all required receiver fields."}), 400

    if not age.isdigit() or int(age) < 1 or int(age) > 120:
        return jsonify({"success": False, "message": "Valid age (1-120) is required."}), 400

    receiver_id = f"ODMS-REC-{datetime.datetime.now().year}-{random.randint(1000, 9999)}"

    with DBWrapper() as db:
        rec_db_id = db.execute(
            """INSERT INTO receivers (receiver_id, name, age, gender, phone, email, blood_group, needed_organ, address, city, emergency_level, contact_number, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Pending')""",
            (receiver_id, name, int(age), gender, phone, email, blood_group,
             needed_organ, address, city, emergency_level, contact_number)
        )

        # Handle Uploaded Health Reports
        reports_dir = os.path.join(app.static_folder, "uploads", "reports")
        os.makedirs(reports_dir, exist_ok=True)

        report_fields = [
            ("blood_test_report", "Blood Test"),
            ("ecg_report", "ECG Report"),
            ("scan_report", "Scan Report"),
            ("medical_certificate", "Medical Certificate")
        ]

        for field_name, report_type in report_fields:
            if field_name in request.files:
                file = request.files[field_name]
                if file and file.filename and allowed_file(file.filename, ALLOWED_REPORT_EXTENSIONS):
                    clean_name = f"report_{receiver_id}_{field_name}_{secure_filename(file.filename)}"
                    save_path = os.path.join(reports_dir, clean_name)
                    file.save(save_path)
                    file_size = os.path.getsize(save_path)
                    rel_url = f"/static/uploads/reports/{clean_name}"
                    db.execute(
                        "INSERT INTO health_reports (receiver_id, report_type, file_path, file_name, file_size) VALUES (%s, %s, %s, %s, %s)",
                        (rec_db_id, report_type, rel_url, file.filename, file_size)
                    )

        # System Notification
        db.execute(
            """INSERT INTO notifications (user_type, user_identifier, title_en, title_ta, message_en, message_ta, type)
               VALUES ('admin', NULL, %s, %s, %s, %s, 'emergency')""",
            (
                f"Urgent Organ Request: {needed_organ} ({blood_group})",
                f"அவசர உறுப்பு தேவை: {needed_organ} ({blood_group})",
                f"Patient {name} in {city} urgently requires a {needed_organ} ({emergency_level} Urgency).",
                f"{city} நகரில் உள்ள {name} அவர்களுக்கு {needed_organ} உறுப்பு உடனடியாக தேவைப்படுகிறது."
            )
        )

    return jsonify({
        "success": True,
        "message": "Receiver requirement registered successfully!",
        "receiver": {
            "receiver_id": receiver_id,
            "name": name,
            "needed_organ": needed_organ,
            "blood_group": blood_group,
            "city": city,
            "emergency_level": emergency_level
        }
    })

# ==========================================================
# BLOOD REQUEST (Requirement #8)
# ==========================================================


@app.route("/api/blood-requests/create", methods=["POST"])
def api_blood_request_create():
    data = request.get_json(silent=True) or {}
    patient_name = (request.form.get("patient_name") or data.get("patient_name") or "").strip()
    blood_group = (request.form.get("blood_group") or data.get("blood_group") or "").strip()
    units_raw = request.form.get("units_required") or data.get("units_required") or 1
    try:
        units_required = max(1, int(units_raw))
    except (ValueError, TypeError):
        units_required = 1
    hospital_name = (request.form.get("hospital_name") or data.get("hospital_name") or "").strip()
    city = (request.form.get("city") or data.get("city") or "").strip()
    emergency_level = (request.form.get("emergency_level") or data.get("emergency_level") or "Urgent").strip()
    contact_number = (request.form.get("contact_number") or data.get("contact_number") or "").strip()

    if not all([patient_name, blood_group, hospital_name, city, contact_number]):
        return jsonify({"success": False, "message": "All fields are required for emergency blood requests."}), 400

    request_id = f"ODMS-BREQ-{datetime.datetime.now().year}-{random.randint(1000, 9999)}"

    with DBWrapper() as db:
        db.execute(
            """INSERT INTO blood_requests (request_id, patient_name, blood_group, units_required, hospital_name, city, emergency_level, contact_number, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'Pending')""",
            (request_id, patient_name, blood_group, units_required, hospital_name, city, emergency_level, contact_number)
        )

        db.execute(
            """INSERT INTO notifications (user_type, user_identifier, title_en, title_ta, message_en, message_ta, type)
               VALUES ('admin', NULL, %s, %s, %s, %s, 'emergency')""",
            (
                f"Emergency Blood Alert: {units_required} Units of {blood_group}",
                f"அவசர ரத்த தேவை: {units_required} யூனிட் {blood_group}",
                f"Patient {patient_name} at {hospital_name}, {city} requires {units_required} units of {blood_group}.",
                f"{hospital_name}, {city} மருத்துவமனையில் {patient_name} அவர்களுக்கு {units_required} யூனிட் {blood_group} தேவை."
            )
        )

    return jsonify({
        "success": True,
        "message": "Emergency blood request posted successfully!",
        "request": {
            "request_id": request_id,
            "patient_name": patient_name,
            "blood_group": blood_group,
            "units_required": units_required,
            "city": city,
            "emergency_level": emergency_level
        }
    })

# ==========================================================
# AI MATCHING & SEARCH (Requirement #6, #8, #9, #10)
# ==========================================================


@app.route("/api/match/organ", methods=["POST"])
def api_match_organ():
    data = request.get_json(silent=True) or request.form or {}
    needed_organ = str(data.get("needed_organ", "Kidney")).strip()
    blood_group = str(data.get("blood_group", "O+")).strip()
    city = str(data.get("city", "Salem")).strip()
    emergency_level = str(data.get("emergency_level", "High")).strip()

    matches = match_organ_donors(needed_organ, blood_group, city, emergency_level)
    return jsonify({"success": True, "matches": matches})


@app.route("/api/match/blood", methods=["POST"])
def api_match_blood():
    data = request.get_json(silent=True) or request.form or {}
    blood_group = str(data.get("blood_group", "O+")).strip()
    city = str(data.get("city", "Salem")).strip()
    units_raw = data.get("units", 1)
    try:
        units = max(1, int(units_raw))
    except (ValueError, TypeError):
        units = 1
    emergency_level = str(data.get("emergency_level", "Urgent")).strip()

    matches = match_blood_donors(blood_group, city, units, emergency_level)
    return jsonify({"success": True, "matches": matches})

# ==========================================================
# ADMIN ACCOUNT SIGN-UP, LOGIN, RESET, DASHBOARD (Requirement #11, #12, #13, #14, #15, #16, #17)
# ==========================================================


@app.route("/api/admin/signup", methods=["POST"])
def api_admin_signup():
    data = request.get_json(silent=True) or {}
    full_name = (request.form.get("full_name") or data.get("full_name") or "").strip()
    email = (request.form.get("email") or data.get("email") or "").strip().lower()
    phone = format_10digit_phone(request.form.get("phone") or data.get("phone") or "")
    password = (request.form.get("password") or data.get("password") or "").strip()
    confirm_password = (request.form.get("confirm_password") or data.get("confirm_password") or "").strip()
    otp_code = (request.form.get("otp_code") or data.get("otp_code") or "").strip()

    if not all([full_name, email, password, confirm_password]):
        return jsonify({"success": False, "message": "Full name, email, and passwords are required."}), 400

    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return jsonify({"success": False, "message": "Please enter a valid email address."}), 400

    if phone and (len(phone) != 10 or not re.match(r"^[6-9]\d{9}$", phone)):
        return jsonify({"success": False, "message": "Please enter a valid 10-digit mobile number starting with 6-9."}), 400

    if password != confirm_password:
        return jsonify({"success": False, "message": "Passwords do not match."}), 400

    if len(password) < 8:
        return jsonify({"success": False, "message": "Password must be at least 8 characters long."}), 400

    if not re.search(r"[A-Z]", password) or not re.search(r"[a-z]", password) or not re.search(r"\d", password):
        return jsonify(
            {"success": False, "message": "Password must include uppercase, lowercase, and numeric characters."}), 400

    with DBWrapper() as db:
        existing = db.query_one("SELECT id FROM admins WHERE LOWER(TRIM(email)) = %s", (email,))
        if existing:
            return jsonify(
                {"success": False, "message": "An admin account with this email address already exists."}), 409

    if not otp_code:
        res = send_email_otp(email, "admin_signup", {"full_name": full_name})
        if not res.get("success"):
            err_msg = res.get("message_en") or "Unable to send OTP. Please try again."
            return jsonify({"success": False, "message": err_msg}), 400
        return jsonify({
            "success": True,
            "message": res.get("message_en") or "OTP has been sent to your registered email address.",
            "email": email,
            "masked_email": get_masked_email(email),
            "expires_in_seconds": res.get("expires_in_seconds", 300),
            "cooldown_seconds": res.get("cooldown_seconds", 60)
        })

    v_res = verify_email_otp(email, otp_code, "admin_signup")
    if not v_res.get("success"):
        return jsonify({"success": False, "message": v_res.get("message_en") or "Invalid OTP. Please try again."}), 401

    username_base = email.split("@")[0].strip().replace(" ", "_") or "admin"
    username_base = re.sub(r"[^A-Za-z0-9_.-]+", "_", username_base)[:30]
    username = username_base
    counter = 1

    with DBWrapper() as db:
        while True:
            existing = db.query_one(
                "SELECT id FROM admins WHERE LOWER(TRIM(email)) = %s OR LOWER(TRIM(username)) = %s",
                (email, username)
            )
            if not existing:
                break
            username = f"{username_base}_{counter}"
            counter += 1

        security_keyword = f"ADMIN-{uuid.uuid4().hex[:12].upper()}"
        hashed_password = generate_password_hash(password, method="pbkdf2:sha256")
        db.execute(
            "INSERT INTO admins (username, email, phone, password_hash, full_name, security_keyword, role) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (username, email, phone, hashed_password, full_name, security_keyword, "Admin")
        )

    return jsonify({
        "success": True,
        "message": "Admin account created successfully. Please sign in with your new credentials.",
        "username": username,
        "email": email,
        "phone": phone
    })


@app.route("/api/admin/login", methods=["POST"])
def api_admin_login():
    data = request.get_json(silent=True) or {}
    email_val = request.form.get("email") or data.get("email") or ""
    user_val = request.form.get("username") or data.get("username") or ""
    identifier = (email_val or user_val).strip().lower()
    password = (request.form.get("password") or data.get("password") or "").strip()
    otp_code = (request.form.get("otp_code") or data.get("otp_code") or "").strip()

    if not identifier or not password:
        return jsonify({"success": False, "message": "Email and password are required."}), 400

    with DBWrapper() as db:
        admin = db.query_one(
            "SELECT * FROM admins WHERE LOWER(TRIM(email)) = %s OR LOWER(TRIM(username)) = %s",
            (identifier, identifier)
        )

    if not admin:
        return jsonify({"success": False, "message": "No admin account found with this email. Please sign up first."}), 401

    if not safe_check_password_hash(admin["password_hash"], password):
        return jsonify({"success": False, "message": "Incorrect password. Please try again."}), 401

    admin_email = admin["email"]

    # Auto-migrate legacy/scrypt hash to pbkdf2 upon verified password check
    if admin.get("password_hash", "").startswith("scrypt:"):
        try:
            with DBWrapper() as db:
                new_h = generate_password_hash(password, method="pbkdf2:sha256")
                db.execute("UPDATE admins SET password_hash = %s WHERE id = %s", (new_h, admin["id"]))
        except Exception:
            pass

    if not otp_code:
        res = send_email_otp(admin_email, "admin_login")
        if not res.get("success"):
            err_msg = res.get("message_en") or "Unable to send OTP. Please try again."
            return jsonify({"success": False, "message": err_msg}), 400
        return jsonify({
            "success": True,
            "message": res.get("message_en") or "OTP has been sent to your registered email address.",
            "masked_email": get_masked_email(admin_email),
            "requires_otp": True,
            "email": admin["email"],
            "expires_in_seconds": res.get("expires_in_seconds", 300),
            "cooldown_seconds": res.get("cooldown_seconds", 60)
        })

    v_res = verify_email_otp(admin_email, otp_code, "admin_login")
    if not v_res.get("success"):
        return jsonify({"success": False, "message": v_res.get("message_en") or "Invalid OTP. Please try again."}), 401

    session.pop("admin_otp_email", None)
    session.pop("admin_otp_attempts", None)

    session["admin_id"] = admin["id"]
    session["admin_username"] = admin["username"]
    session["admin_email"] = admin["email"]
    session["admin_phone"] = admin.get("phone")
    session["admin_role"] = admin.get("role", "Admin")

    return jsonify({"success": True, "message": "Admin login successful!"})


@app.route("/api/admin/reset-password", methods=["POST"])
def api_admin_reset_password():
    data = request.get_json(silent=True) or {}
    email_val = request.form.get("email") or data.get("email") or ""
    user_val = request.form.get("username") or data.get("username") or ""
    identifier = (email_val or user_val).strip().lower()

    form_otp = request.form.get("otp_code") or request.form.get("security_keyword")
    json_otp = data.get("otp_code") or data.get("security_keyword")
    otp_code = (form_otp or json_otp or "").strip()

    new_password = (request.form.get("new_password") or data.get("new_password") or "").strip()
    confirm_password = (request.form.get("confirm_password") or data.get("confirm_password") or "").strip()

    if not identifier:
        return jsonify({"success": False, "message": "Admin email or username is required."}), 400

    with DBWrapper() as db:
        admin = db.query_one(
            "SELECT * FROM admins WHERE LOWER(TRIM(email)) = %s OR LOWER(TRIM(username)) = %s",
            (identifier, identifier)
        )
    if not admin:
        return jsonify({"success": False, "message": "No admin account found with this email. Please sign up first."}), 404

    admin_email = admin["email"]

    if not otp_code and not new_password and not confirm_password:
        res = send_email_otp(admin_email, "admin_reset_password")
        if not res.get("success"):
            err_msg = res.get("message_en") or "Unable to send OTP. Please try again."
            return jsonify({"success": False, "message": err_msg}), 400
        return jsonify({
            "success": True,
            "message": res.get("message_en") or "OTP has been sent to your registered email address.",
            "masked_email": get_masked_email(admin_email),
            "expires_in_seconds": res.get("expires_in_seconds", 300),
            "cooldown_seconds": res.get("cooldown_seconds", 60)
        })

    if not all([identifier, otp_code, new_password, confirm_password]):
        return jsonify({"success": False, "message": "Admin email, OTP, and new passwords are required."}), 400

    if new_password != confirm_password:
        return jsonify({"success": False, "message": "Passwords do not match."}), 400

    if len(new_password) < 8:
        return jsonify({"success": False, "message": "Password must be at least 8 characters long."}), 400

    if not re.search(r"[A-Z]", new_password) or not re.search(r"[a-z]", new_password) or not re.search(r"\d", new_password):
        return jsonify(
            {"success": False, "message": "Password must include uppercase, lowercase, and numeric characters."}), 400

    v_res = verify_email_otp(admin_email, otp_code, "admin_reset_password")
    if not v_res.get("success"):
        err_msg = v_res.get("message_en") or "Invalid or expired OTP verification code."
        return jsonify({"success": False, "message": err_msg}), 401

    new_hash = generate_password_hash(new_password, method="pbkdf2:sha256")
    with DBWrapper() as db:
        db.execute("UPDATE admins SET password_hash = %s WHERE id = %s", (new_hash, admin["id"]))

    return jsonify({"success": True, "message": "Password reset successfully! You can now sign in with your new password."})


@app.route("/api/admin/logout", methods=["POST", "GET"])
def api_admin_logout():
    session.clear()
    return jsonify({"success": True, "message": "Admin logged out successfully."})


@app.route("/api/admin/check-session", methods=["GET"])
def api_admin_check_session():
    is_logged_in = ("admin_id" in session)
    return jsonify({
        "success": True,
        "is_logged_in": is_logged_in,
        "username": session.get("admin_username"),
        "email": session.get("admin_email")
    })


@app.route("/api/admin/stats", methods=["GET"])
def api_admin_stats():
    with DBWrapper() as db:
        total_donors = db.query_one("SELECT COUNT(*) as count FROM donors")["count"]
        total_blood_donors = db.query_one("SELECT COUNT(*) as count FROM blood_donors")["count"]
        total_receivers = db.query_one("SELECT COUNT(*) as count FROM receivers")["count"]
        total_blood_requests = db.query_one("SELECT COUNT(*) as count FROM blood_requests")["count"]

        pending_donors = db.query_one("SELECT COUNT(*) as count FROM donors WHERE status = 'Pending'")["count"]
        approved_donors = db.query_one("SELECT COUNT(*) as count FROM donors WHERE status = 'Approved'")["count"]
        rejected_donors = db.query_one("SELECT COUNT(*) as count FROM donors WHERE status = 'Rejected'")["count"]

        pending_blood_donors = db.query_one(
            "SELECT COUNT(*) as count FROM blood_donors WHERE status = 'Pending'")["count"]
        approved_blood_donors = db.query_one(
            "SELECT COUNT(*) as count FROM blood_donors WHERE status = 'Approved'")["count"]
        rejected_blood_donors = db.query_one(
            "SELECT COUNT(*) as count FROM blood_donors WHERE status = 'Rejected'")["count"]

        pending_receivers = db.query_one("SELECT COUNT(*) as count FROM receivers WHERE status = 'Pending'")["count"]
        approved_receivers = db.query_one("SELECT COUNT(*) as count FROM receivers WHERE status = 'Approved'")["count"]
        rejected_receivers = db.query_one("SELECT COUNT(*) as count FROM receivers WHERE status = 'Rejected'")["count"]

        pending_requests = db.query_one(
            "SELECT COUNT(*) as count FROM blood_requests WHERE status = 'Pending'")["count"]
        approved_requests = db.query_one(
            "SELECT COUNT(*) as count FROM blood_requests WHERE status = 'Approved'")["count"]
        rejected_requests = db.query_one(
            "SELECT COUNT(*) as count FROM blood_requests WHERE status = 'Rejected'")["count"]

        hospitals_count = db.query_one(
            "SELECT COUNT(DISTINCT hospital_name) as count FROM blood_requests WHERE TRIM(hospital_name) != ''")["count"]
        total_matches = 0

    pending_total = pending_donors + pending_blood_donors + pending_receivers + pending_requests
    approved_total = approved_donors + approved_blood_donors + approved_receivers + approved_requests
    rejected_total = rejected_donors + rejected_blood_donors + rejected_receivers + rejected_requests

    return jsonify({
        "success": True,
        "stats": {
            "total_donors": total_donors,
            "total_blood_donors": total_blood_donors,
            "total_receivers": total_receivers,
            "total_blood_requests": total_blood_requests,
            "pending_donors": pending_donors,
            "approved_donors": approved_donors,
            "pending_requests": pending_requests,
            "rejected_total": rejected_total,
            "approved_total": approved_total,
            "pending_total": pending_total,
            "total_matches": total_matches,
            "hospital_count": hospitals_count,
            "quick_organ_donors": total_donors,
            "quick_blood_donors": total_blood_donors,
            "quick_find_organ": total_receivers,
            "quick_blood_requests": total_blood_requests
        }
    })


@app.route("/api/admin/donors", methods=["GET"])
def api_admin_donors():
    if not session.get("admin_id"):
        return jsonify({"success": False, "message": "Admin login required."}), 401
    with DBWrapper() as db:
        donors = db.query("SELECT * FROM donors ORDER BY id DESC")
    return jsonify({"success": True, "donors": donors})


@app.route("/api/admin/donors/<int:donor_db_id>", methods=["GET"])
def api_admin_get_donor(donor_db_id):
    if not session.get("admin_id"):
        return jsonify({"success": False, "message": "Admin login required."}), 401
    with DBWrapper() as db:
        donor = db.query_one("SELECT * FROM donors WHERE id = %s", (donor_db_id,))
    if not donor:
        return jsonify({"success": False, "message": "Donor record not found."}), 404
    return jsonify({"success": True, "donor": donor})


@app.route("/api/admin/donors/<int:donor_db_id>", methods=["DELETE"])
def api_admin_delete_donor(donor_db_id):
    if not session.get("admin_id"):
        return jsonify({"success": False, "message": "Admin login required."}), 401
    with DBWrapper() as db:
        db.execute("DELETE FROM donors WHERE id = %s", (donor_db_id,))
    return jsonify({"success": True, "message": "Donor deleted successfully."})


@app.route("/api/admin/donors/<int:donor_db_id>/status", methods=["POST"])
def api_admin_donor_status(donor_db_id):
    if not session.get("admin_id"):
        return jsonify({"success": False, "message": "Admin login required."}), 401
    data = request.get_json(silent=True) or {}
    new_status = (data.get("status") or request.form.get("status") or "Approved").strip()
    valid_statuses = {"Pending", "Approved", "Rejected"}
    if new_status not in valid_statuses:
        return jsonify({"success": False, "message": "Invalid status selected."}), 400
    with DBWrapper() as db:
        existing = db.query_one("SELECT id, status FROM donors WHERE id = %s", (donor_db_id,))
        if not existing:
            return jsonify({"success": False, "message": "Donor record not found."}), 404
        if (existing["status"] or "").strip() == new_status:
            return jsonify({"success": True, "message": f"Status already {new_status}", "status": new_status})
        db.execute("UPDATE donors SET status = %s WHERE id = %s", (new_status, donor_db_id))
    return jsonify({"success": True, "message": f"Status updated to {new_status}", "status": new_status})


@app.route("/api/admin/receivers", methods=["GET"])
def api_admin_receivers():
    if not session.get("admin_id"):
        return jsonify({"success": False, "message": "Admin login required."}), 401
    with DBWrapper() as db:
        receivers = db.query("SELECT * FROM receivers ORDER BY id DESC")
    return jsonify({"success": True, "receivers": receivers})


@app.route("/api/admin/receivers/<int:receiver_id>", methods=["GET"])
def api_admin_get_receiver(receiver_id):
    if not session.get("admin_id"):
        return jsonify({"success": False, "message": "Admin login required."}), 401
    with DBWrapper() as db:
        receiver = db.query_one("SELECT * FROM receivers WHERE id = %s", (receiver_id,))
        if not receiver:
            return jsonify({"success": False, "message": "Receiver record not found."}), 404
        reports = db.query(
            "SELECT report_type, file_path, file_name FROM health_reports WHERE receiver_id = %s", (receiver_id,))
    return jsonify({"success": True, "receiver": receiver, "health_reports": reports})


@app.route("/api/admin/receivers/<int:receiver_id>", methods=["DELETE"])
def api_admin_delete_receiver(receiver_id):
    if not session.get("admin_id"):
        return jsonify({"success": False, "message": "Admin login required."}), 401
    with DBWrapper() as db:
        db.execute("DELETE FROM receivers WHERE id = %s", (receiver_id,))
    return jsonify({"success": True, "message": "Receiver deleted successfully."})


@app.route("/api/admin/receivers/<int:receiver_id>/status", methods=["POST"])
def api_admin_receiver_status(receiver_id):
    if not session.get("admin_id"):
        return jsonify({"success": False, "message": "Admin login required."}), 401
    data = request.get_json(silent=True) or {}
    new_status = (data.get("status") or request.form.get("status") or "Approved").strip()
    valid_statuses = {"Pending", "Approved", "Rejected"}
    if new_status not in valid_statuses:
        return jsonify({"success": False, "message": "Invalid status selected."}), 400
    with DBWrapper() as db:
        existing = db.query_one("SELECT id, status FROM receivers WHERE id = %s", (receiver_id,))
        if not existing:
            return jsonify({"success": False, "message": "Receiver record not found."}), 404
        if (existing["status"] or "").strip() == new_status:
            return jsonify({"success": True, "message": f"Status already {new_status}", "status": new_status})
        db.execute("UPDATE receivers SET status = %s WHERE id = %s", (new_status, receiver_id))
    return jsonify({"success": True, "message": f"Status updated to {new_status}", "status": new_status})


@app.route("/api/admin/blood-donors", methods=["GET"])
def api_admin_blood_donors():
    if not session.get("admin_id"):
        return jsonify({"success": False, "message": "Admin login required."}), 401
    with DBWrapper() as db:
        blood_donors = db.query("SELECT * FROM blood_donors ORDER BY id DESC")
    return jsonify({"success": True, "blood_donors": blood_donors})


@app.route("/api/admin/blood-donors/<int:blood_donor_id>", methods=["GET"])
def api_admin_get_blood_donor(blood_donor_id):
    if not session.get("admin_id"):
        return jsonify({"success": False, "message": "Admin login required."}), 401
    with DBWrapper() as db:
        donor = db.query_one("SELECT * FROM blood_donors WHERE id = %s", (blood_donor_id,))
    if not donor:
        return jsonify({"success": False, "message": "Blood donor record not found."}), 404
    return jsonify({"success": True, "blood_donor": donor})


@app.route("/api/admin/blood-donors/<int:blood_donor_id>", methods=["DELETE"])
def api_admin_delete_blood_donor(blood_donor_id):
    if not session.get("admin_id"):
        return jsonify({"success": False, "message": "Admin login required."}), 401
    with DBWrapper() as db:
        db.execute("DELETE FROM blood_donors WHERE id = %s", (blood_donor_id,))
    return jsonify({"success": True, "message": "Blood donor deleted successfully."})


@app.route("/api/admin/blood-donors/<int:blood_donor_id>/status", methods=["POST"])
def api_admin_blood_donor_status(blood_donor_id):
    if not session.get("admin_id"):
        return jsonify({"success": False, "message": "Admin login required."}), 401
    data = request.get_json(silent=True) or {}
    new_status = (data.get("status") or request.form.get("status") or "Approved").strip()
    valid_statuses = {"Pending", "Approved", "Rejected"}
    if new_status not in valid_statuses:
        return jsonify({"success": False, "message": "Invalid status selected."}), 400
    with DBWrapper() as db:
        existing = db.query_one("SELECT id, status FROM blood_donors WHERE id = %s", (blood_donor_id,))
        if not existing:
            return jsonify({"success": False, "message": "Blood donor record not found."}), 404
        if (existing["status"] or "").strip() == new_status:
            return jsonify({"success": True, "message": f"Status already {new_status}", "status": new_status})
        db.execute("UPDATE blood_donors SET status = %s WHERE id = %s", (new_status, blood_donor_id))
    return jsonify({"success": True, "message": f"Status updated to {new_status}", "status": new_status})


@app.route("/api/admin/blood-requests", methods=["GET"])
def api_admin_blood_requests():
    if not session.get("admin_id"):
        return jsonify({"success": False, "message": "Admin login required."}), 401
    with DBWrapper() as db:
        blood_requests = db.query("SELECT * FROM blood_requests ORDER BY id DESC")
    return jsonify({"success": True, "requests": blood_requests})


@app.route("/api/admin/blood-requests/<int:blood_request_id>", methods=["GET"])
def api_admin_get_blood_request(blood_request_id):
    if not session.get("admin_id"):
        return jsonify({"success": False, "message": "Admin login required."}), 401
    with DBWrapper() as db:
        breq = db.query_one("SELECT * FROM blood_requests WHERE id = %s", (blood_request_id,))
    if not breq:
        return jsonify({"success": False, "message": "Blood request not found."}), 404
    return jsonify({"success": True, "request": breq})


@app.route("/api/admin/blood-requests/<int:blood_request_id>", methods=["DELETE"])
def api_admin_delete_blood_request(blood_request_id):
    if not session.get("admin_id"):
        return jsonify({"success": False, "message": "Admin login required."}), 401
    with DBWrapper() as db:
        db.execute("DELETE FROM blood_requests WHERE id = %s", (blood_request_id,))
    return jsonify({"success": True, "message": "Blood request deleted successfully."})


@app.route("/api/admin/blood-requests/<int:blood_request_id>/status", methods=["POST"])
def api_admin_blood_request_status(blood_request_id):
    if not session.get("admin_id"):
        return jsonify({"success": False, "message": "Admin login required."}), 401
    data = request.get_json(silent=True) or {}
    new_status = (data.get("status") or request.form.get("status") or "Approved").strip()
    valid_statuses = {"Pending", "Approved", "Rejected"}
    if new_status not in valid_statuses:
        return jsonify({"success": False, "message": "Invalid status selected."}), 400
    with DBWrapper() as db:
        existing = db.query_one("SELECT id, status FROM blood_requests WHERE id = %s", (blood_request_id,))
        if not existing:
            return jsonify({"success": False, "message": "Blood request record not found."}), 404
        if (existing["status"] or "").strip() == new_status:
            return jsonify({"success": True, "message": f"Status already {new_status}", "status": new_status})
        db.execute("UPDATE blood_requests SET status = %s WHERE id = %s", (new_status, blood_request_id))
    return jsonify({"success": True, "message": f"Status updated to {new_status}", "status": new_status})


@app.route("/api/admin/records/<table_name>/<int:record_id>", methods=["DELETE"])
def api_admin_delete_record(table_name, record_id):
    if not session.get("admin_id"):
        return jsonify({"success": False, "message": "Admin login required."}), 401
    allowed_tables = ["donors", "receivers", "blood_donors", "blood_requests", "notifications"]
    if table_name not in allowed_tables:
        return jsonify({"success": False, "message": "Invalid table."}), 400

    with DBWrapper() as db:
        db.execute(f"DELETE FROM {table_name} WHERE id = %s", (record_id,))
    return jsonify({"success": True, "message": "Record deleted successfully."})

# ==========================================================
# NOTIFICATIONS (Requirement #21)
# ==========================================================


@app.route("/api/notifications", methods=["GET"])
def api_notifications():
    with DBWrapper() as db:
        notifications = db.query("SELECT * FROM notifications ORDER BY id DESC LIMIT 30")
    return jsonify({"success": True, "notifications": notifications})

# ==========================================================
# ERROR HANDLERS
# ==========================================================


@app.errorhandler(404)
def handle_404(e):
    if request.path.startswith("/api/"):
        return jsonify({"success": False, "message": "API endpoint not found"}), 404
    return render_template("index.html"), 404


@app.errorhandler(413)
def handle_413(e):
    if request.path.startswith("/api/"):
        return jsonify({"success": False, "message": "Uploaded file exceeds maximum allowed size (16MB)"}), 413
    return "File too large (Max 16MB)", 413


@app.errorhandler(500)
def handle_500(e):
    if request.path.startswith("/api/"):
        return jsonify({"success": False, "message": "Internal Server Error"}), 500
    return "Internal Server Error", 500


if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", 5000))
    debug = os.getenv("DEBUG", "False").lower() == "true"
    print("==================================================")
    print(" LifeSaver Organ & Blood Donation System Running")
    print(f" URL: http://127.0.0.1:{port}")
    print(" Bilingual: English + Tamil")
    print("==================================================")
    app.run(host="0.0.0.0", port=port, debug=debug)
