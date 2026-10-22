# Organ and Blood Donation Management System (ODMS)
### Bilingual Platform: English + Tamil (தமிழ்)
A production-grade, state-of-the-art Healthcare Web Application built with **Flask**, **MySQL**, **ReportLab PDF generation**, **QR Code Verification**, **AI-Assisted Matching Algorithm**, **OTP Security**, **Health Report File Uploads**, and **Form State Persistence**.

---

## 🌟 Key Features

1. **Dual Language Support (English / தமிழ்)**:
   - Dynamic real-time language switcher in the top navigation bar.
   - Comprehensive dictionary covering all forms, buttons, alerts, and tables.
   - Saves language choice in `localStorage`.

2. **Organ Donor Registration & Digital Card**:
   - Fields: Full Name, Age (18+), Gender, Phone Number, OTP Verification, Email, Blood Group (A+, A-, B+, B-, AB+, AB-, O+, O-), Organ Checklist (Kidney, Liver, Heart, Lung, Pancreas, Eye), Address, City Autocomplete, Medical History, Availability Status, Donor Photo upload.
   - **Prerequisite Validation**: "Send OTP" button is strictly disabled until Full Name, Age (18+), Gender, and valid 10-digit Phone are entered.
   - **Automatic PDF Generation**: Generates official, high-resolution Donor Card PDF via ReportLab.
   - **QR Code Verification**: Generates embedded QR code linking to public verification page (`/verify-donor/<donor_id>`).
   - **Automated Emailing**: Dispatches the generated PDF card directly to the donor's email address.

3. **Blood Donor Registration**:
   - Validates age eligibility (18–65 years) and interval since last donation date (>90 days).
   - Instant phone OTP verification and duplicate registration prevention.

4. **Receiver Registration & Clinical Uploads**:
   - Records needed organ, patient details, emergency level (Low, Medium, High, Critical).
   - Securely uploads and validates medical reports (Blood Test, ECG, CT/MRI Scan, Medical Certificate) up to 16MB.

5. **Urgent Blood Request Portal**:
   - Posts urgent emergency blood requirements by hospital and required units.
   - Automatically searches and alerts compatible active blood donors.

6. **Intelligent AI Matching Algorithm**:
   - **Organ Matching Matrix**: ABO/Rh blood compatibility (35%), mandatory organ match, geographic distance / city coordinates (20%), emergency level multiplier (20%), donor availability (15%), verification status (10%).
   - **Blood Matching Matrix**: Compatibility matrix (40%), distance (25%), emergency urgency (20%), donation recency (15%).
   - Transparent breakdown modal ("Why this score?") and medical disclaimer notice.

7. **Central Administrator Portal & Dashboard**:
   - Secure login with hashed passwords (`pbkdf2:sha256`) and 2FA OTP verification.
   - **Multi-Step Forgot Password Recovery**: Username -> Security Keyword -> New Password -> Instant Hash update.
   - Live database statistics counters.
   - Complete Data Tables: Organ Donors, Receivers, Blood Donors, Blood Requests.
   - Actions: Approve, Reject, View PDF Card, Match Donors, Delete records.

8. **User Experience & Accessibility**:
   - **Page State / Form Persistence**: Form fields auto-save to `sessionStorage` in real-time. Switching between pages and returning restores unfinished form data!
   - **Auto-Next Field Navigation**: Pressing `Enter` sequentially focuses the next form input without premature submission.
   - **City Suggestion System**: Autocomplete dropdown for Tamil Nadu & Indian cities (Salem, Chennai, Coimbatore, Madurai, Trichy, Erode, Tirunelveli, etc.).
   - **Real-Time Notification Center**: Live bell alert with unread badge count for emergency requests and registrations.

---

## 📁 Project Directory Structure

```
c:/xampp1/htdocs/Organ Donation/
├── app.py                      # Main Flask Application & REST API Endpoints
├── database.py                 # MySQL Database Connection Manager & Query Wrapper
├── schema.sql                  # Complete MySQL Database Creation & Seed Script
├── requirements.txt            # Python Dependencies
├── .env.example                # Environment Configuration Template
├── .env                        # Local Environment Variables
├── test_system.py              # Unit Test Suite
├── e2e_verification.py         # End-to-End Integration Test Suite
├── services/
│   ├── __init__.py
│   ├── otp_service.py          # 6-Digit OTP Generation, Expiry & Verification
│   ├── matching.py             # Intelligent AI Matching & Proximity Calculation
│   ├── pdf_generator.py        # ReportLab Digital Donor Card PDF Generator
│   ├── qr_service.py           # Scannable Verification QR Code Generator
│   └── email_service.py        # SMTP Mailer with PDF Attachment Support
├── static/
│   ├── css/
│   │   └── style.css           # Premium Responsive Healthcare Design System
│   ├── js/
│   │   ├── i18n.js             # Bilingual English + Tamil Translation Engine
│   └── app.js              # Client-Side Controller, Form Persistence & Autocomplete
│   ├── img/
│   │   └── default-avatar.png  # Default Avatar Asset
│   └── uploads/
│       ├── photos/             # Uploaded Donor Photos
│       ├── reports/            # Uploaded Receiver Medical Reports
│       ├── qrcodes/            # Generated Verification QR Codes
│       └── cards/              # Generated Donor Card PDFs
└── templates/
    ├── index.html              # Single-Page Application (SPA) Container with all Tabs
    └── verify_donor.html       # Public Tamper-Proof QR Verification Page
```

---

## ⚙️ Installation & Setup Guide

### 1. Prerequisites
- Python 3.9+ installed
- XAMPP / WAMP or standalone MySQL Server

### 2. Install Python Dependencies
Open PowerShell or Command Prompt in the project folder and run:
```powershell
pip install -r requirements.txt
```

### 3. Setup MySQL Database
1. Open **XAMPP Control Panel** and start **MySQL**.
2. Open **phpMyAdmin** (`http://localhost/phpmyadmin`) or MySQL CLI.
3. The system automatically initializes the MySQL database tables on first launch.
   - Or import manually via Command Line:
     ```powershell
     & "c:\xampp1\mysql\bin\mysql.exe" -u root < schema.sql
     ```

### 4. Configure Environment Variables (`.env`)
Create/check the `.env` file in the root folder:
```ini
SECRET_KEY=organ_donation_secret_key_2026_secure_random
FLASK_ENV=development
FLASK_PORT=5000
DEBUG=True

# MySQL Configuration
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=organdonar

# SMS Gateway Configuration (Twilio / Fast2SMS / Custom REST)
SMS_GATEWAY_PROVIDER=twilio
TWILIO_ACCOUNT_SID=your-account-sid
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_PHONE_NUMBER=+1234567890
# FAST2SMS_API_KEY=your-fast2sms-key

# SMTP Email Configuration
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=noreply@organdonation.org

# Application Base URL (for QR code linking)
APP_BASE_URL=http://localhost:5000
```

### 5. Start the Flask Web Server
Run:
```powershell
python app.py
```
Open your browser and navigate to:
👉 **`http://127.0.0.1:5000`**

---

## 🧪 Testing & Verification Guide

### 1. Automated Test Suites
Run the backend test suite:
```powershell
python test_system.py
```
Run the live end-to-end integration suite:
```powershell
python e2e_verification.py
```

### 2. Manual User Workflows

#### A. Bilingual Language Switch
- Select **தமிழ்** or **English** from the Language selector in the navbar to seamlessly switch the entire page.

#### B. Testing Organ Donor Registration & OTP
1. Click **Organ Pledge** (`#organ-donor`).
2. Notice that the **Send OTP** button is disabled until valid info is entered.
3. Enter Full Name, Age (18+), Gender, and 10-digit Phone (`9876543210`).
4. Click **Send OTP**. A secure 6-digit random OTP is generated and dispatched via SMS.
5. Enter the 6-digit OTP received and click **Verify OTP**.
6. Fill in Blood Group, City (`Salem` with autocomplete), Address, Pledged Organs, and optional photo.
7. Click **Complete Organ Pledge Registration**.
8. The **Digital Donor Card** tab opens automatically displaying the newly generated card, photo, QR code, and **Download PDF** link!

#### C. Testing AI Matching System
1. Click **Search & Match** (`#search-match`).
2. Select Organ: `Kidney`, Blood Group: `O+` or `B+`, City: `Salem`, Urgency: `High`.
3. Click **Find Compatible Donors**.
4. Observe the matching cards showing **AI Match Score**, distance calculation in km, and breakdown details.

#### D. Testing Admin Portal
1. Click **Admin Portal** (`#admin-login`).
2. Credentials:
   - **Email**: `organdonation@gmail.com`
   - **Password**: `AdminPassword@2026`
   - Click **Send OTP** to receive a 6-digit random code on the registered admin email.
   - Enter the OTP code and click **Login to Dashboard**.
3. View live statistics, Organ Donors table (with Approve/Reject/View PDF actions), Receivers table, Blood Donors table, and Blood Requests.

#### E. Testing QR Code Verification
Open:
👉 **`http://127.0.0.1:5000/verify-donor/ODMS-ORG-2026-1001`**
Verify the safe donor verification badge and privacy-shielded information.

---

## 🔒 Security Implementations

- **SQL Injection Prevention**: 100% parameterized queries.
- **Password Security**: PBKDF2 with SHA-256 password hashing.
- **Input Validation**: Strict Regex for 10-digit Indian phone numbers (`^[6-9]\d{9}$`) and valid emails.
- **Medical Privacy**: Personal phone numbers and private clinical notes are masked on public match cards and QR verification pages.
- **File Upload Protection**: Validates extensions (`.pdf`, `.jpg`, `.png`), enforces secure filenames, and restricts maximum upload size to 16MB.
