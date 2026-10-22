import io
import json
import os
import unittest
import warnings

from app import app
from database import DBWrapper, init_database
from services.email_service import get_last_dispatched_email_otp
from services.matching import match_blood_donors, match_organ_donors
from services.otp_service import (
    send_mobile_otp,
    send_registration_otp,
    verify_mobile_otp,
    verify_registration_otp
)
from services.pdf_generator import generate_donor_card_pdf
from services.qr_service import generate_donor_qr
from services.sms_service import get_last_dispatched_sms_otp
from werkzeug.security import generate_password_hash

warnings.simplefilter("ignore")
os.environ["PYTHONWARNINGS"] = "ignore"
os.environ["UNIT_TEST_MODE"] = "1"


class TestOrganDonationSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_database()
        cls.client = app.test_client()

    @classmethod
    def tearDownClass(cls):
        """Clean up temporary test records to keep exactly 5 records per table."""
        with DBWrapper() as db:
            db.execute(
                "DELETE FROM donors WHERE phone = '9876599991' OR email = 'test.donor.unit@example.com'"
            )
            db.execute(
                "DELETE FROM blood_donors WHERE phone = '9845099992' OR email = 'test.bld.unit@example.com'"
            )
            db.execute(
                "DELETE FROM blood_requests WHERE contact_number = '9845099999' OR patient_name = 'Unit Test Emergency Patient'"
            )
            db.execute("DELETE FROM admins WHERE email = 'newadminsignup@example.com'")
            db.execute(
                "DELETE FROM otp_verifications WHERE phone_or_email IN "
                "('9876543210', '9876512345', '9876554321', '9876588888', "
                "'verify.email.donor@example.com', 'newadminsignup@example.com', "
                "'test.donor.unit@example.com', 'test.bld.unit@example.com')"
            )

    def test_01_otp_prerequisites_and_generation(self):
        """Test OTP prerequisite constraints, cryptographically random generation, and verification."""
        test_phone = "9876543210"
        with DBWrapper() as db:
            db.execute("DELETE FROM otp_verifications WHERE phone_or_email = %s", (test_phone,))

        # Missing full name should fail
        res = send_registration_otp(
            test_phone, "organ_donor", {
                "full_name": "", "age": 25, "gender": "Male", "phone": test_phone})
        self.assertFalse(res["success"])

        # Underage should fail
        res = send_registration_otp(
            test_phone, "organ_donor", {
                "full_name": "Test Donor", "age": 16, "gender": "Male", "phone": test_phone})
        self.assertFalse(res["success"])

        # Valid prerequisites should succeed and generate a random 6-digit OTP
        res = send_registration_otp(
            test_phone, "organ_donor", {
                "full_name": "Test Donor", "age": 25, "gender": "Male", "phone": test_phone})
        self.assertTrue(res["success"])
        self.assertEqual(res.get("expires_in_seconds"), 300)
        # OTP must not be exposed in public API response
        self.assertNotIn("test_otp", res)
        self.assertNotIn("otp", res)
        self.assertNotIn("otp_code", res)

        # Retrieve the genuine random OTP from SMS dispatcher cache
        real_otp = get_last_dispatched_sms_otp(test_phone)
        self.assertIsNotNone(real_otp)
        self.assertEqual(len(real_otp), 6)
        self.assertTrue(real_otp.isdigit())

        # Check that the database stores a 64-character SHA-256 salted hash, NOT plaintext OTP
        with DBWrapper() as db:
            otp_record = db.query_one(
                "SELECT otp_code FROM otp_verifications WHERE phone_or_email = %s ORDER BY id DESC LIMIT 1",
                (test_phone,)
            )
        self.assertIsNotNone(otp_record)
        stored_hash = otp_record["otp_code"]
        self.assertEqual(len(stored_hash), 64)
        self.assertNotEqual(stored_hash, real_otp)

        # Arbitrary / fixed OTP (e.g. 123456 or 000000) must FAIL
        v_fail = verify_registration_otp(test_phone, "000000" if real_otp != "000000" else "111111", "organ_donor")
        self.assertFalse(v_fail["success"])

        # Real random OTP must SUCCEED
        v_ok = verify_registration_otp(test_phone, real_otp, "organ_donor")
        self.assertTrue(v_ok["success"])

    def test_02_qr_and_pdf_generation(self):
        """Test generating QR code and official ReportLab PDF card."""
        test_id = "ODMS-ORG-2026-TEST"
        qr_web, qr_path = generate_donor_qr(test_id)
        self.assertTrue(os.path.exists(qr_path))

        donor_data = {
            "donor_id": test_id,
            "full_name": "Test Lifesaver",
            "blood_group": "O+",
            "organ_type": "Kidney, Liver, Eye",
            "city": "Salem",
            "status": "Approved"
        }
        pdf_web, pdf_path = generate_donor_card_pdf(donor_data)
        self.assertTrue(os.path.exists(pdf_path))
        self.assertTrue(os.path.getsize(pdf_path) > 1000)

    def test_03_ai_organ_matching(self):
        """Test AI Organ Matching algorithm."""
        matches = match_organ_donors("Kidney", "O+", "Salem", "High")
        self.assertIsInstance(matches, list)
        self.assertTrue(len(matches) > 0)
        top_match = matches[0]
        self.assertIn("match_score", top_match)
        self.assertIn("score_breakdown", top_match)
        self.assertTrue(top_match["match_score"] >= 70.0)

    def test_04_ai_blood_matching(self):
        """Test AI Blood Matching algorithm."""
        matches = match_blood_donors("O+", "Salem", 2, "Urgent")
        self.assertIsInstance(matches, list)
        self.assertTrue(len(matches) > 0)
        self.assertIn("match_score", matches[0])

    def test_05_admin_signup_and_login_flow(self):
        """Test the requested Email OTP-based admin sign-up and sign-in flow with random OTP."""
        signup_email = "newadminsignup@example.com"
        signup_phone = "9876500001"
        signup_password = "NewAdmin@2026"

        with DBWrapper() as db:
            db.execute("DELETE FROM admins WHERE LOWER(email) = %s OR phone = %s", (signup_email.lower(), signup_phone))
            db.execute("DELETE FROM otp_verifications WHERE phone_or_email = %s", (signup_email.lower(),))

        # 1. First signup call without OTP initiates registration and sends Email OTP
        signup_res = self.client.post("/api/admin/signup", data={
            "full_name": "New Admin User",
            "email": signup_email,
            "phone": signup_phone,
            "password": signup_password,
            "confirm_password": signup_password,
        })
        self.assertEqual(signup_res.status_code, 200)
        signup_json = json.loads(signup_res.data)
        self.assertTrue(signup_json["success"])
        self.assertIn("masked_email", signup_json)
        # Ensure raw OTP is not leaked
        self.assertNotIn("otp", signup_json)
        self.assertNotIn("otp_code", signup_json)

        with DBWrapper() as db:
            self.assertIsNone(db.query_one("SELECT id FROM admins WHERE LOWER(email) = %s", (signup_email.lower(),)))

        # 2. Fetch dynamically generated random Email OTP from dispatcher cache
        signup_otp = get_last_dispatched_email_otp(signup_email)
        self.assertIsNotNone(signup_otp)
        self.assertEqual(len(signup_otp), 6)

        # 3. Submit complete signup with random Email OTP
        create_res = self.client.post("/api/admin/signup", data={
            "full_name": "New Admin User",
            "email": signup_email,
            "phone": signup_phone,
            "password": signup_password,
            "confirm_password": signup_password,
            "otp_code": signup_otp
        })
        self.assertEqual(create_res.status_code, 200)
        self.assertTrue(json.loads(create_res.data)["success"])

        # Verify admin created in DB
        with DBWrapper() as db:
            admin_db = db.query_one("SELECT * FROM admins WHERE LOWER(email) = %s", (signup_email.lower(),))
        self.assertIsNotNone(admin_db)
        self.assertEqual(admin_db["email"], signup_email)

        # 4. Request login OTP with valid credentials (Step 1 of 2FA)
        login_otp_res = self.client.post("/api/admin/login", data={
            "email": signup_email,
            "password": signup_password
        })
        self.assertEqual(login_otp_res.status_code, 200)
        login_otp_json = json.loads(login_otp_res.data)
        self.assertTrue(login_otp_json["success"])
        self.assertTrue(login_otp_json.get("requires_otp"))
        self.assertIn("masked_email", login_otp_json)

        # 5. Retrieve random Email login OTP and complete 2FA login (Step 2)
        login_otp = get_last_dispatched_email_otp(signup_email)
        self.assertIsNotNone(login_otp)

        login_res = self.client.post("/api/admin/login", data={
            "email": signup_email,
            "password": signup_password,
            "otp_code": login_otp
        })
        self.assertEqual(login_res.status_code, 200)
        self.assertTrue(json.loads(login_res.data)["success"])

    def test_06_admin_auth_routes_and_not_found_message(self):
        """Ensure separate admin auth routes exist and the not-found message matches the requested flow."""
        fresh_client = app.test_client()

        signin_route = fresh_client.get("/admin/signin")
        self.assertEqual(signin_route.status_code, 200)
        signup_route = fresh_client.get("/admin/signup")
        self.assertEqual(signup_route.status_code, 200)

        missing_account = fresh_client.post("/api/admin/login", data={
            "email": "missing.admin.user@example.com",
            "password": "NoPassword@2026",
            "otp_code": "123456"
        })
        self.assertEqual(missing_account.status_code, 401)
        self.assertIn("No admin account found with this email. Please sign up first.",
                      json.loads(missing_account.data)["message"])

    def test_07_admin_login_and_stats(self):
        """Test Admin login with Email OTP and live statistics endpoint."""
        admin_email = "organdonation@gmail.com"
        admin_pass = "AdminPassword@2026"

        with DBWrapper() as db:
            db.execute("DELETE FROM otp_verifications WHERE phone_or_email = %s AND purpose = 'admin_login'", (admin_email.lower(),))

        # Step 1: Send OTP via login initiate
        send_res = self.client.post("/api/admin/login", data={
            "email": admin_email,
            "password": admin_pass
        })
        self.assertEqual(send_res.status_code, 200)

        admin_otp = get_last_dispatched_email_otp(admin_email)
        self.assertIsNotNone(admin_otp)

        res = self.client.post("/api/admin/login", data={
            "email": admin_email,
            "password": admin_pass,
            "otp_code": admin_otp
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["success"])

        stats_res = self.client.get("/api/admin/stats")
        self.assertEqual(stats_res.status_code, 200)
        stats_data = json.loads(stats_res.data)
        self.assertTrue(stats_data["success"])
        self.assertTrue(stats_data["stats"]["total_donors"] >= 1)

    def test_07b_public_qr_verification_endpoint(self):
        """Test public donor verification endpoint."""
        with DBWrapper() as db:
            donor = db.query_one("SELECT donor_id FROM donors ORDER BY id DESC LIMIT 1")
        test_donor_id = donor["donor_id"] if donor else "ODMS-ORG-2026-TEST"
        res = self.client.get(f"/verify-donor/{test_donor_id}")
        self.assertEqual(res.status_code, 200)
        if donor:
            self.assertIn(test_donor_id.encode("utf-8"), res.data)

    def test_08_admin_forgot_password_and_logout(self):
        """Test Admin Email OTP send, forgot password reset flow, and logout."""
        admin_email = "organdonation@gmail.com"

        with DBWrapper() as db:
            db.execute("DELETE FROM otp_verifications WHERE phone_or_email = %s", (admin_email.lower(),))

        # 1. Request OTP for reset
        reset_init_res = self.client.post("/api/admin/reset-password", data={
            "email": admin_email
        })
        self.assertEqual(reset_init_res.status_code, 200)
        self.assertTrue(json.loads(reset_init_res.data)["success"])

        # Fetch reset OTP from Email cache
        reset_otp = get_last_dispatched_email_otp(admin_email)
        self.assertIsNotNone(reset_otp)

        # 2. Reset Password with Email OTP
        new_pwd = "NewSecureAdmin@2026"
        reset_res = self.client.post("/api/admin/reset-password", data={
            "email": admin_email,
            "otp_code": reset_otp,
            "new_password": new_pwd,
            "confirm_password": new_pwd
        })
        self.assertEqual(reset_res.status_code, 200)
        reset_data = json.loads(reset_res.data)
        self.assertTrue(reset_data["success"])

        # 3. Request new login OTP for the updated password (clear prior verification entry for test)
        with DBWrapper() as db:
            db.execute("DELETE FROM otp_verifications WHERE phone_or_email = %s", (admin_email.lower(),))

        login_init_res = self.client.post("/api/admin/login", data={
            "email": admin_email,
            "password": new_pwd
        })
        self.assertEqual(login_init_res.status_code, 200)
        new_login_otp = get_last_dispatched_email_otp(admin_email)
        self.assertIsNotNone(new_login_otp)

        # 4. Verify Login with New Password and Email OTP
        login_res = self.client.post("/api/admin/login", data={
            "email": admin_email,
            "password": new_pwd,
            "otp_code": new_login_otp
        })
        self.assertEqual(login_res.status_code, 200)
        self.assertTrue(json.loads(login_res.data)["success"])

        # 5. Test Logout
        logout_res = self.client.post("/api/admin/logout")
        self.assertEqual(logout_res.status_code, 200)
        self.assertTrue(json.loads(logout_res.data)["success"])

        # 6. Restore default password for test repeatability
        with DBWrapper() as db:
            db.execute(
                "UPDATE admins SET password_hash = %s WHERE LOWER(email) = %s",
                (generate_password_hash("AdminPassword@2026"), admin_email.lower())
            )

    def test_08_verify_ui_security_and_hospitals_removal(self):
        """Verify Partner Hospitals, About Us, Contact, and Home stats cards are removed."""
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")
        self.assertNotIn("Partner Hospitals", html)
        self.assertNotIn("heroStatHospitals", html)
        self.assertNotIn("42+", html)
        self.assertNotIn("about-story", html)
        self.assertNotIn("contact-section", html)
        self.assertNotIn("homeStatTotalDonors", html)
        self.assertNotIn("homeStatOrganDonors", html)
        self.assertNotIn("homeStatBloodDonors", html)
        self.assertNotIn("homeStatBloodReqs", html)
        self.assertNotIn("stats-section", html)
        self.assertNotIn("stat-panel", html)
        self.assertNotIn("nav_brand_sub", html)
        self.assertNotIn("ORGAN & BLOOD REGISTRY", html)
        self.assertNotIn('data-i18n="process_kicker"', html)
        self.assertNotIn('data-i18n="process_title"', html)
        self.assertNotIn("process-section", html)
        self.assertNotIn('data-i18n="organs_kicker"', html)
        self.assertNotIn('data-i18n="organs_title"', html)
        self.assertNotIn("organs-section", html)
        self.assertNotIn('data-i18n="blood_kicker"', html)
        self.assertNotIn('data-i18n="blood_title"', html)
        self.assertNotIn("blood-section", html)
        self.assertNotIn('data-i18n="search_panel_kicker"', html)
        self.assertNotIn('data-i18n="search_panel_title"', html)
        self.assertNotIn('data-i18n="features_kicker"', html)
        self.assertNotIn('data-i18n="features_title"', html)
        self.assertNotIn("features-section", html)
        self.assertNotIn('data-i18n="cta_banner_kicker"', html)
        self.assertNotIn('data-i18n="cta_banner_title"', html)
        self.assertNotIn("cta-banner", html)
        self.assertIn("btn-back", html)
        self.assertIn("admin_email", html)
        self.assertIn("btnSendAdminLoginOtp", html)

    def test_09_donor_registration_endpoint(self):
        """Test Organ Donor complete registration flow: validation, duplicate check, unique ID, PDF, QR, MySQL persistence, and email."""
        test_phone = "9876599991"
        test_email = "test.donor.unit@example.com"

        # Clear any prior record with this phone/email
        with DBWrapper() as db:
            db.execute("DELETE FROM donors WHERE phone = %s OR email = %s", (test_phone, test_email))

        # 1. Validation test: Missing name should fail
        res_fail_name = self.client.post("/api/donors/register", data={
            "full_name": "",
            "age": "28",
            "gender": "Female",
            "phone": test_phone,
            "email": test_email,
            "blood_group": "A+",
            "organ_type": "Kidney, Eye",
            "address": "123 Test Street",
            "city": "Salem"
        })
        self.assertEqual(res_fail_name.status_code, 400)

        # 2. Validation test: Invalid phone format (e.g. 5 digits or invalid prefix)
        res_fail_phone = self.client.post("/api/donors/register", data={
            "full_name": "Unit Test Donor",
            "age": "28",
            "gender": "Female",
            "phone": "12345",
            "email": test_email,
            "blood_group": "A+",
            "organ_type": "Kidney, Eye",
            "address": "123 Test Street",
            "city": "Salem"
        })
        self.assertEqual(res_fail_phone.status_code, 400)

        # 3. Successful Registration flow
        res = self.client.post("/api/donors/register", data={
            "full_name": "Unit Test Donor",
            "age": "28",
            "gender": "Female",
            "phone": test_phone,
            "email": test_email,
            "blood_group": "A+",
            "organ_type": "Kidney, Eye, Liver",
            "address": "123 Test Street",
            "city": "Salem",
            "medical_history": "Healthy non-smoker",
            "availability_status": "Available"
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertIn("donor", data)
        donor_id = data["donor"]["donor_id"]
        self.assertTrue(donor_id.startswith("ODMS-ORG-"))
        self.assertIn("Donor Registration Successful", data["message"])

        # 4. Check PDF and QR Code were generated on disk
        pdf_url = data["donor"]["pdf_url"]
        qr_url = data["donor"]["qr_code_url"]
        pdf_disk_path = os.path.join(app.static_folder, pdf_url.replace("/static/", "").replace("/", os.sep))
        qr_disk_path = os.path.join(app.static_folder, qr_url.replace("/static/", "").replace("/", os.sep))
        self.assertTrue(os.path.exists(pdf_disk_path))
        self.assertTrue(os.path.exists(qr_disk_path))

        # 5. Check MySQL database persistence
        with DBWrapper() as db:
            saved_donor = db.query_one("SELECT * FROM donors WHERE donor_id = %s", (donor_id,))
            self.assertIsNotNone(saved_donor)
            self.assertEqual(saved_donor["phone"], test_phone)
            self.assertEqual(saved_donor["email"], test_email)
            self.assertEqual(saved_donor["blood_group"], "A+")
            self.assertEqual(saved_donor["status"], "Approved")

        # 6. Check Duplicate phone prevention
        res_dup_phone = self.client.post("/api/donors/register", data={
            "full_name": "Duplicate Phone Donor",
            "age": "30",
            "gender": "Male",
            "phone": test_phone,
            "email": "different.email@example.com",
            "blood_group": "B+",
            "organ_type": "Heart",
            "address": "456 Other St",
            "city": "Chennai"
        })
        self.assertEqual(res_dup_phone.status_code, 400)
        dup_phone_data = json.loads(res_dup_phone.data)
        self.assertFalse(dup_phone_data["success"])
        self.assertIn("already registered", dup_phone_data["message"])

        # 7. Check Duplicate email prevention
        res_dup_email = self.client.post("/api/donors/register", data={
            "full_name": "Duplicate Email Donor",
            "age": "30",
            "gender": "Male",
            "phone": "9876543219",
            "email": test_email,
            "blood_group": "B+",
            "organ_type": "Heart",
            "address": "456 Other St",
            "city": "Chennai"
        })
        self.assertEqual(res_dup_email.status_code, 400)
        dup_email_data = json.loads(res_dup_email.data)
        self.assertFalse(dup_email_data["success"])
        self.assertIn("already registered", dup_email_data["message"])

        # 8. Test Resend Donor Card API endpoint
        resend_res = self.client.post(f"/api/donors/{donor_id}/resend-card")
        self.assertEqual(resend_res.status_code, 200)
        resend_data = json.loads(resend_res.data)
        self.assertTrue(resend_data["success"])

    def test_10_blood_donor_and_request_endpoints(self):
        """Test Blood Donor direct registration (no OTP) and Emergency Blood Request API endpoints."""
        bld_phone = "9845099992"
        bld_email = "test.bld.unit@example.com"

        with DBWrapper() as db:
            db.execute("DELETE FROM blood_donors WHERE phone = %s OR email = %s", (bld_phone, bld_email))

        # Register blood donor directly with photo upload (no OTP required)
        photo_bytes = io.BytesIO(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82")
        res = self.client.post("/api/blood-donors/register", data={
            "full_name": "Unit Test Blood Donor",
            "age": "26",
            "gender": "Male",
            "phone": bld_phone,
            "email": bld_email,
            "blood_group": "B+",
            "last_donation_date": "2026-01-15",
            "address": "45 Blood Road",
            "city": "Chennai",
            "availability_status": "Available",
            "photo": (photo_bytes, "donor_avatar.png")
        }, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["success"])

        # Verify photo_url was stored in DB
        with DBWrapper() as db:
            saved_donor = db.query_one("SELECT photo_url FROM blood_donors WHERE phone = %s", (bld_phone,))
            self.assertIsNotNone(saved_donor)
            self.assertTrue(saved_donor["photo_url"].startswith("/static/uploads/photos/"))

        # Create emergency blood request
        breq_res = self.client.post("/api/blood-requests/create", data={
            "patient_name": "Unit Test Emergency Patient",
            "blood_group": "B+",
            "units_required": "2",
            "hospital_name": "City General Hospital",
            "city": "Chennai",
            "emergency_level": "Critical",
            "contact_number": "9845099999"
        })
        self.assertEqual(breq_res.status_code, 200)
        breq_data = json.loads(breq_res.data)
        self.assertTrue(breq_data["success"])

    def test_11_otp_cooldown_and_security(self):
        """Test 60-second resend cooldown security."""
        cooldown_phone = "9876512345"

        with DBWrapper() as db:
            db.execute("DELETE FROM otp_verifications WHERE phone_or_email = %s", (cooldown_phone,))

        # 1. First send succeeds
        send1 = self.client.post("/send-mobile-otp", json={
            "phone": cooldown_phone,
            "purpose": "test_cooldown",
            "prerequisite_data": {"full_name": "Cooldown Tester", "age": 22, "gender": "Male", "phone": cooldown_phone}
        })
        self.assertEqual(send1.status_code, 200)

        # 2. Immediate resend is blocked by cooldown
        send2 = self.client.post("/send-mobile-otp", json={
            "phone": cooldown_phone,
            "purpose": "test_cooldown",
            "prerequisite_data": {"full_name": "Cooldown Tester", "age": 22, "gender": "Male", "phone": cooldown_phone}
        })
        self.assertEqual(send2.status_code, 400)
        send2_data = json.loads(send2.data)
        self.assertFalse(send2_data["success"])
        self.assertTrue(send2_data.get("cooldown_seconds", 0) > 0)

    def test_12_email_otp_flow(self):
        """Test Email OTP separate dispatch and verification endpoint."""
        email_target = "verify.email.donor@example.com"

        with DBWrapper() as db:
            db.execute("DELETE FROM otp_verifications WHERE LOWER(phone_or_email) = %s", (email_target.lower(),))

        # 1. Send Email OTP
        send_res = self.client.post("/send-email-otp", json={
            "email": email_target,
            "purpose": "email_verification"
        })
        self.assertEqual(send_res.status_code, 200)
        self.assertTrue(json.loads(send_res.data)["success"])

        # 2. Retrieve random OTP from cache
        generated_otp = get_last_dispatched_email_otp(email_target)
        self.assertIsNotNone(generated_otp)

        # 3. Wrong OTP fails
        wrong_verify = self.client.post("/verify-email-otp", json={
            "email": email_target,
            "otp": "000000" if generated_otp != "000000" else "111111",
            "purpose": "email_verification"
        })
        self.assertEqual(wrong_verify.status_code, 400)
        self.assertFalse(json.loads(wrong_verify.data)["success"])

        # 4. Correct OTP succeeds
        ok_verify = self.client.post("/verify-email-otp", json={
            "email": email_target,
            "otp": generated_otp,
            "purpose": "email_verification"
        })
        self.assertEqual(ok_verify.status_code, 200)
        self.assertTrue(json.loads(ok_verify.data)["success"])

    def test_13_otp_max_attempts_invalidation(self):
        """Test that exceeding 5 incorrect attempts permanently invalidates the OTP."""
        test_phone = "9876554321"
        with DBWrapper() as db:
            db.execute("DELETE FROM otp_verifications WHERE phone_or_email = %s", (test_phone,))

        # Send fresh OTP
        send_res = send_mobile_otp(
            test_phone, "attempt_test", {
                "full_name": "Attempt Tester", "age": 25, "gender": "Male", "phone": test_phone})
        self.assertTrue(send_res["success"])
        real_otp = get_last_dispatched_sms_otp(test_phone)

        # 4 failed attempts should give remaining attempts warning
        for i in range(1, 5):
            res = verify_mobile_otp(test_phone, "999999", "attempt_test")
            self.assertFalse(res["success"])
            self.assertIn(f"{5 - i} attempt(s) remaining", res["message_en"])

        # 5th failed attempt should lock and invalidate the OTP
        res5 = verify_mobile_otp(test_phone, "999999", "attempt_test")
        self.assertFalse(res5["success"])
        self.assertIn("Maximum attempts reached", res5["message_en"])

        # Even with the correct OTP, subsequent verification must now FAIL
        res_locked = verify_mobile_otp(test_phone, real_otp, "attempt_test")
        self.assertFalse(res_locked["success"])

    def test_14_zero_otp_leak_security(self):
        """Verify that no OTP is ever leaked in public HTTP responses."""
        test_phone = "9876588888"
        with DBWrapper() as db:
            db.execute("DELETE FROM otp_verifications WHERE phone_or_email = %s", (test_phone,))

        res = self.client.post("/send-mobile-otp", json={
            "phone": test_phone,
            "purpose": "leak_test",
            "prerequisite_data": {"full_name": "Leak Tester", "age": 30, "gender": "Male", "phone": test_phone}
        })
        self.assertEqual(res.status_code, 200)
        data_text = res.data.decode("utf-8")
        real_otp = get_last_dispatched_sms_otp(test_phone)

        # OTP string must never appear in response body
        self.assertNotIn(f'"{real_otp}"', data_text)
        self.assertNotIn(f"'{real_otp}'", data_text)
        self.assertNotIn("otp_code", data_text)
        self.assertNotIn("test_otp", data_text)

    def test_15_donor_registration_form_field_structure(self):
        """Verify exact field structures and sequence for Organ Donor and Blood Donor forms without OTP."""
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")

        # 1. ORGAN DONOR FORM: Check exact sequence of IDs (Requirement #10)
        organ_expected_ids = [
            'id="organ_name"',
            'id="organ_age"',
            'id="organ_gender"',
            'id="organ_phone"',
            'id="organ_blood_group"',
            'name="organ_types"',
            'id="organ_address"',
            'id="organ_city"',
            'id="organ_medical"',
            'id="organ_avail"',
            'id="organ_photo"',
            'id="organ_email"'
        ]
        organ_form_start = html.find('id="organDonorForm"')
        organ_form_end = html.find('</form>', organ_form_start)
        organ_form_html = html[organ_form_start:organ_form_end]

        last_pos = 0
        for field_id in organ_expected_ids:
            pos = organ_form_html.find(field_id)
            self.assertNotEqual(pos, -1, f"Missing field {field_id} in Organ Donor form")
            self.assertGreater(pos, last_pos, f"Field {field_id} is out of order in Organ Donor form")
            last_pos = pos

        # 2. BLOOD DONOR FORM: Check exact sequence of IDs
        blood_expected_ids = [
            'id="bld_name"',
            'id="bld_age"',
            'id="bld_gender"',
            'id="bld_phone"',
            'id="bld_email"',
            'id="bld_group"',
            'id="bld_last_date"',
            'id="bld_address"',
            'id="bld_city"',
            'id="bld_avail"',
            'id="bld_photo"'
        ]
        blood_form_start = html.find('id="bloodDonorForm"')
        blood_form_end = html.find('</form>', blood_form_start)
        blood_form_html = html[blood_form_start:blood_form_end]

        last_pos = 0
        for field_id in blood_expected_ids:
            pos = blood_form_html.find(field_id)
            self.assertNotEqual(pos, -1, f"Missing field {field_id} in Blood Donor form")
            self.assertGreater(pos, last_pos, f"Field {field_id} is out of order in Blood Donor form")
            last_pos = pos

        # 3. Ensure NO OTP fields or buttons in either form
        self.assertNotIn("btnSendOrganOtp", organ_form_html)
        self.assertNotIn("btnVerifyOrganOtp", organ_form_html)
        self.assertNotIn("organ_otp_input", organ_form_html)
        self.assertNotIn("organOtpBox", organ_form_html)
        self.assertNotIn("organVerifiedBadge", organ_form_html)

        self.assertNotIn("btnSendBloodOtp", blood_form_html)
        self.assertNotIn("btnVerifyBloodOtp", blood_form_html)
        self.assertNotIn("bld_otp_input", blood_form_html)
        self.assertNotIn("bloodOtpBox", blood_form_html)
        self.assertNotIn("bloodVerifiedBadge", blood_form_html)

        # 4. Ensure Admin Login OTP is still present
        self.assertIn("btnSendAdminLoginOtp", html)
        self.assertIn("admin_login_otp", html)


if __name__ == "__main__":
    unittest.main()
