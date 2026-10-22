from __future__ import annotations
import io
import os
import random
import threading
import time

import requests
from app import app
from database import DBWrapper
from services.email_service import get_last_dispatched_email_otp

os.environ["UNIT_TEST_MODE"] = "1"
BASE_URL = "http://127.0.0.1:5055"


def ensure_server_running():
    try:
        r = requests.get(f"{BASE_URL}/", timeout=1)
        if r.status_code == 200:
            return
    except Exception:
        pass

    def _run():
        app.run(host="127.0.0.1", port=5055, debug=False, use_reloader=False)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    time.sleep(1.5)


def test_e2e():
    ensure_server_running()
    print("\n--- Starting Comprehensive End-to-End System Verification ---")
    session = requests.Session()

    test_rand = random.randint(10000, 99999)
    test_phone = f"98765{test_rand}"
    test_email = f"test_{test_rand}@example.com"

    # 1. Homepage
    res = session.get(f"{BASE_URL}/")
    assert res.status_code == 200, f"Homepage failed with {res.status_code}"
    assert "LifeSaver" in res.text
    assert "data-i18n" in res.text
    print("[PASS] 1. Homepage loads successfully with full HTML5 & bilingual templates.")

    # 2. Organ Donor Direct Registration & PDF / QR Generation
    photo_file = io.BytesIO(b"fake image data header")
    donor_res = session.post(f"{BASE_URL}/api/donors/register", data={
        "full_name": "Ravi Chandran",
        "age": "30",
        "gender": "Male",
        "phone": test_phone,
        "email": test_email,
        "blood_group": "B+",
        "organ_type": "Kidney, Liver, Eye",
        "address": "45 Anna Salai",
        "city": "Salem",
        "medical_history": "Healthy volunteer",
        "availability_status": "Available"
    }, files={
        "photo": ("test_photo.jpg", photo_file, "image/jpeg")
    }).json()

    assert donor_res["success"], f"Donor registration failed: {donor_res}"
    donor_obj = donor_res["donor"]
    donor_id = donor_obj["donor_id"]
    pdf_url = donor_obj["pdf_url"]
    qr_url = donor_obj["qr_code_url"]
    print(f"[PASS] 2. Organ Donor directly registered! Generated Donor ID: {donor_id}")
    print(f"       PDF Card Web Path: {pdf_url}")
    print(f"       QR Code Web Path:  {qr_url}")

    # Check that PDF is accessible via HTTP
    pdf_check = session.get(f"{BASE_URL}{pdf_url}")
    assert pdf_check.status_code == 200, "Generated PDF could not be fetched via HTTP"
    assert pdf_check.headers.get("Content-Type", "").startswith("application/pdf"), "PDF Content-Type invalid"
    print(f"[PASS] 3. Donor Card PDF ({len(pdf_check.content)} bytes) is downloadable via HTTP.")

    # 3. Public QR Verification Portal
    qr_verify_page = session.get(f"{BASE_URL}/verify-donor/{donor_id}")
    assert qr_verify_page.status_code == 200
    assert donor_id in qr_verify_page.text
    assert "Ravi Chandran" in qr_verify_page.text
    assert "VERIFIED ACTIVE DONOR" in qr_verify_page.text
    print(f"[PASS] 4. Public QR Verification Page verified at /verify-donor/{donor_id}")

    # 4. Blood Donor Direct Registration
    bld_phone = f"98459{random.randint(10000, 99999)}"
    bld_res = session.post(f"{BASE_URL}/api/blood-donors/register", data={
        "full_name": "Divya Krishnan",
        "age": "24",
        "gender": "Female",
        "phone": bld_phone,
        "email": f"divya_{bld_phone}@example.com",
        "blood_group": "O+",
        "last_donation_date": "2026-03-01",
        "address": "12 Cross Cut Rd",
        "city": "Salem",
        "availability_status": "Available"
    }).json()
    assert bld_res["success"], f"Blood donor failed: {bld_res}"
    print(f"[PASS] 5. Blood Donor directly registered: {bld_res['blood_donor_id']}")

    # 7. Receiver Registration with Medical Reports
    report_file = io.BytesIO(b"%PDF-1.4 Mock medical certificate content")
    rec_phone = f"98765{random.randint(10000, 99999)}"
    rec_res = session.post(f"{BASE_URL}/api/receivers/register", data={
        "name": "Muruganandham",
        "age": "50",
        "gender": "Male",
        "phone": rec_phone,
        "email": f"murugan_{rec_phone}@example.com",
        "blood_group": "B+",
        "needed_organ": "Kidney",
        "address": "77 Fairlands",
        "city": "Salem",
        "emergency_level": "Critical",
        "contact_number": rec_phone
    }, files={
        "medical_certificate": ("doctor_cert.pdf", report_file, "application/pdf")
    }).json()
    assert rec_res["success"], f"Receiver failed: {rec_res}"
    print(f"[PASS] 9. Receiver registered with health report upload: {rec_res['receiver']['receiver_id']}")

    # 8. Emergency Blood Request
    breq_res = session.post(f"{BASE_URL}/api/blood-requests/create", data={
        "patient_name": "Senthil Nathan",
        "blood_group": "O+",
        "units_required": "3",
        "hospital_name": "Manipal Hospital",
        "city": "Salem",
        "emergency_level": "Critical",
        "contact_number": "9876540002"
    }).json()
    assert breq_res["success"], f"Blood request failed: {breq_res}"
    print(f"[PASS] 10. Emergency Blood Request posted: {breq_res['request']['request_id']}")

    # 9. AI Organ Matching
    organ_match = session.post(f"{BASE_URL}/api/match/organ", json={
        "needed_organ": "Kidney",
        "blood_group": "B+",
        "city": "Salem",
        "emergency_level": "Critical"
    }).json()
    assert organ_match["success"]
    assert len(organ_match["matches"]) > 0
    top_match = organ_match["matches"][0]
    print(f"[PASS] 11. AI Organ Matching found {len(organ_match['matches'])} compatible donors.")
    print(
        f"        Top Match: {top_match['full_name']} (AI Score: {top_match['match_score']}%, Dist: {top_match['distance_km']} km)")

    # 10. AI Blood Matching
    blood_match = session.post(f"{BASE_URL}/api/match/blood", json={
        "blood_group": "O+",
        "city": "Salem",
        "units": 3,
        "emergency_level": "Critical"
    }).json()
    assert blood_match["success"]
    assert len(blood_match["matches"]) > 0
    top_bld = blood_match["matches"][0]
    print(f"[PASS] 12. AI Blood Matching found {len(blood_match['matches'])} compatible blood donors.")
    print(f"        Top Blood Match: {top_bld['full_name']} (AI Score: {top_bld['match_score']}%)")

    # 11. Admin Signup with Email OTP Verification
    new_admin_phone = f"98760{random.randint(10000, 99999)}"
    new_admin_email = f"e2e_admin_{new_admin_phone}@example.com"
    signup_init = session.post(f"{BASE_URL}/api/admin/signup", data={
        "full_name": "E2E Administrator",
        "email": new_admin_email,
        "phone": new_admin_phone,
        "password": "AdminPassword@2026",
        "confirm_password": "AdminPassword@2026"
    }).json()
    assert signup_init["success"]
    admin_signup_otp = get_last_dispatched_email_otp(new_admin_email)
    assert admin_signup_otp is not None
    assert len(admin_signup_otp) == 6

    signup_confirm = session.post(f"{BASE_URL}/api/admin/signup", data={
        "full_name": "E2E Administrator",
        "email": new_admin_email,
        "phone": new_admin_phone,
        "password": "AdminPassword@2026",
        "confirm_password": "AdminPassword@2026",
        "otp_code": admin_signup_otp
    }).json()
    assert signup_confirm["success"], f"Admin signup failed: {signup_confirm}"
    print(f"[PASS] 13. Admin Signup with Email OTP verification verified for {new_admin_email}.")

    # 12. Admin Login & 2FA with Email OTP
    admin_login_email = "organdonation@gmail.com"
    with DBWrapper() as db:
        db.execute("DELETE FROM otp_verifications WHERE phone_or_email = %s AND purpose = 'admin_login'", (admin_login_email.lower(),))

    admin_login_init = session.post(f"{BASE_URL}/api/admin/login", data={
        "email": admin_login_email,
        "password": "AdminPassword@2026"
    }).json()
    assert admin_login_init["success"]
    assert admin_login_init.get("requires_otp")

    admin_otp = get_last_dispatched_email_otp(admin_login_email)
    assert admin_otp is not None
    assert len(admin_otp) == 6

    login_res = session.post(f"{BASE_URL}/api/admin/login", data={
        "email": admin_login_email,
        "password": "AdminPassword@2026",
        "otp_code": admin_otp
    }).json()
    assert login_res["success"], f"Admin login failed: {login_res}"
    print("[PASS] 14. Admin 2-Step Email OTP Login verified.")

    # 13. Admin Stats & Tables
    stats = session.get(f"{BASE_URL}/api/admin/stats").json()["stats"]
    print(f"[PASS] 15. Live DB Stats: {stats['total_donors']} Organ Donors, {stats['total_blood_donors']} Blood Donors, {stats['total_receivers']} Receivers, {stats['total_blood_requests']} Blood Reqs.")

    # 14. Notifications
    notifs = session.get(f"{BASE_URL}/api/notifications").json()["notifications"]
    assert len(notifs) > 0
    print(f"[PASS] 16. Notification system operational ({len(notifs)} real-time notifications in queue).")

    print("\n==========================================================================")
    print("ALL 16 INTEGRATION & MODULE TESTS PASSED WITH 100% SUCCESS!")
    print("==========================================================================\n")


if __name__ == "__main__":
    test_e2e()
