import os
import sys
import requests
from database import DBWrapper, init_database

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

BASE_URL = "http://127.0.0.1:5000"


def test_full_donor_registration_flow():
    print("==================================================")
    print("E2E TESTING: DONOR REGISTRATION COMPLETE FLOW")
    print("==================================================")

    init_database()

    test_phone = "9840123456"
    test_email = "selvam.ramanathan@example.com"
    test_name = "Selvam Ramanathan"

    # 0. Clean prior test records
    with DBWrapper() as db:
        db.execute("DELETE FROM donors WHERE phone = %s OR email = %s", (test_phone, test_email))
        print("[Setup] Cleaned previous records for phone/email.")

    # 1. TEST: Missing Required Fields
    print("\n[Step 1] Testing Validation for Missing Required Fields...")
    res1 = requests.post(f"{BASE_URL}/api/donors/register", data={
        "full_name": "",
        "age": "32",
        "gender": "Male",
        "phone": test_phone,
        "email": test_email,
        "blood_group": "O+",
        "organ_type": "Kidney, Liver, Eye",
        "address": "14 Anna Salai, Guindy",
        "city": "Chennai"
    })
    assert res1.status_code == 400, f"Expected 400 for empty name, got {res1.status_code}"
    print("✓ Missing Name blocked with message:", res1.json().get("message"))

    # 2. TEST: Invalid Phone Number
    print("\n[Step 2] Testing Validation for Invalid Phone Number...")
    res2 = requests.post(f"{BASE_URL}/api/donors/register", data={
        "full_name": test_name,
        "age": "32",
        "gender": "Male",
        "phone": "5551234",  # invalid prefix and length
        "email": test_email,
        "blood_group": "O+",
        "organ_type": "Kidney, Liver, Eye",
        "address": "14 Anna Salai, Guindy",
        "city": "Chennai"
    })
    assert res2.status_code == 400, f"Expected 400 for invalid phone, got {res2.status_code}"
    print("✓ Invalid Phone blocked with message:", res2.json().get("message"))

    # 3. TEST: Successful Complete Registration Flow
    print("\n[Step 3] Testing Successful Donor Registration...")
    res3 = requests.post(f"{BASE_URL}/api/donors/register", data={
        "full_name": test_name,
        "age": "32",
        "gender": "Male",
        "phone": test_phone,
        "email": test_email,
        "blood_group": "O+",
        "organ_type": "Kidney, Liver, Eye",
        "address": "14 Anna Salai, Guindy",
        "city": "Chennai",
        "medical_history": "None - Healthy donor",
        "availability_status": "Available"
    })
    assert res3.status_code == 200, f"Expected 200 for valid registration, got {res3.status_code}: {res3.text}"
    data3 = res3.json()
    assert data3["success"] is True
    donor = data3["donor"]
    donor_id = data3["donor_id"]
    print("✓ Registration Successful! Generated Donor ID:", donor_id)
    print("✓ Response Message:", data3["message"])

    # 4. TEST: Database Record Verification in MySQL
    print("\n[Step 4] Verifying MySQL Database Record...")
    with DBWrapper() as db:
        saved_donor = db.query_one("SELECT * FROM donors WHERE donor_id = %s", (donor_id,))
        assert saved_donor is not None, "Donor record missing in MySQL!"
        assert saved_donor["full_name"] == test_name
        assert saved_donor["phone"] == test_phone
        assert saved_donor["email"] == test_email
        assert saved_donor["blood_group"] == "O+"
        assert saved_donor["organ_type"] == "Kidney, Liver, Eye"
        assert saved_donor["city"] == "Chennai"
        assert saved_donor["status"] == "Approved"
        print("✓ MySQL Record Verified: ID =", saved_donor["id"], "| Donor ID =", saved_donor["donor_id"])

    # 5. TEST: PDF Donor Card and QR Code Generation Verification
    print("\n[Step 5] Verifying PDF Card and QR Code Generation on Disk...")
    pdf_url = donor["pdf_url"]
    qr_url = donor["qr_code_url"]
    base_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_path = os.path.join(base_dir, pdf_url.lstrip("/"))
    qr_path = os.path.join(base_dir, qr_url.lstrip("/"))

    assert os.path.exists(pdf_path), f"PDF file not found at {pdf_path}"
    assert os.path.getsize(pdf_path) > 1000, "PDF file is empty or corrupted"
    assert os.path.exists(qr_path), f"QR code file not found at {qr_path}"
    print(f"✓ PDF Card verified on disk ({os.path.getsize(pdf_path)} bytes): {pdf_url}")
    print(f"✓ QR Code verified on disk ({os.path.getsize(qr_path)} bytes): {qr_url}")

    # 6. TEST: Verification Page (when QR is scanned)
    print("\n[Step 6] Testing QR Verification Page Endpoint...")
    verify_res = requests.get(f"{BASE_URL}/verify-donor/{donor_id}")
    assert verify_res.status_code == 200
    assert test_name in verify_res.text
    assert donor_id in verify_res.text
    print(f"✓ QR Verification Endpoint (/verify-donor/{donor_id}) is live and verified!")

    # 7. TEST: Duplicate Phone Prevention
    print("\n[Step 7] Testing Duplicate Phone Prevention...")
    dup_phone_res = requests.post(f"{BASE_URL}/api/donors/register", data={
        "full_name": "Another Person",
        "age": "29",
        "gender": "Female",
        "phone": test_phone,  # same phone
        "email": "another.email@example.com",
        "blood_group": "A+",
        "organ_type": "Heart",
        "address": "50 Mount Road",
        "city": "Chennai"
    })
    assert dup_phone_res.status_code == 400
    dup_phone_data = dup_phone_res.json()
    assert dup_phone_data["success"] is False
    assert "already registered" in dup_phone_data["message"]
    print("✓ Duplicate Phone successfully blocked:", dup_phone_data["message"])

    # 8. TEST: Duplicate Email Prevention
    print("\n[Step 8] Testing Duplicate Email Prevention...")
    dup_email_res = requests.post(f"{BASE_URL}/api/donors/register", data={
        "full_name": "Another Person",
        "age": "29",
        "gender": "Female",
        "phone": "9840999888",
        "email": test_email,  # same email
        "blood_group": "A+",
        "organ_type": "Heart",
        "address": "50 Mount Road",
        "city": "Chennai"
    })
    assert dup_email_res.status_code == 400
    dup_email_data = dup_email_res.json()
    assert dup_email_data["success"] is False
    assert "already registered" in dup_email_data["message"]
    print("✓ Duplicate Email successfully blocked:", dup_email_data["message"])

    # 9. TEST: Resend Email Endpoint
    print("\n[Step 9] Testing Resend Donor Card PDF to Email Endpoint...")
    resend_res = requests.post(f"{BASE_URL}/api/donors/{donor_id}/resend-card")
    assert resend_res.status_code == 200
    resend_data = resend_res.json()
    assert resend_data["success"] is True
    print("✓ Resend Card Endpoint Response:", resend_data["message"])

    # 10. TEST: HTML Form Field Sequence in index.html
    print("\n[Step 10] Verifying HTML Form Field Order & Enter Navigation Map...")
    index_res = requests.get(f"{BASE_URL}/")
    assert index_res.status_code == 200
    html = index_res.text

    expected_sequence = [
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
        'id="organ_email"',
        'id="btnSubmitOrganDonor"'
    ]

    last_idx = 0
    for field in expected_sequence:
        pos = html.find(field)
        assert pos != -1, f"Field {field} not found in HTML"
        assert pos > last_idx, f"Field {field} is out of sequence in HTML"
        last_idx = pos
    print("✓ HTML Form Field Sequence matches required order: Name -> Age -> Phone -> Blood Group -> Organ Type -> Address -> City -> Medical History -> Availability Status -> Donor Photo -> Email -> Submit Button!")

    print("\n==================================================")
    print("ALL 11 DONOR REGISTRATION REQUIREMENTS FULLY VERIFIED!")
    print("==================================================")


if __name__ == "__main__":
    test_full_donor_registration_flow()
