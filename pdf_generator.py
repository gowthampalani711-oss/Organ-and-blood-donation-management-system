import os
import datetime
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from services.qr_service import generate_donor_qr


def generate_donor_card_pdf(donor_data):
    """
    Generates a professional Donor Card PDF with ReportLab.
    Includes Header, Donor Photo, Name, Donor ID, Blood Group, Organ Type, City, Registration Date, QR Code, Verification Seal.
    """
    donor_id = donor_data.get("donor_id", "ODMS-ORG-2026-0000")
    full_name = donor_data.get("full_name", "Anonymous Donor")
    blood_group = donor_data.get("blood_group", "O+")
    organ_type = donor_data.get("organ_type", "All Organs")
    city = donor_data.get("city", "Salem")
    status = donor_data.get("status", "Approved")
    created_at = donor_data.get("created_at", datetime.datetime.now().strftime("%d-%b-%Y"))
    if isinstance(created_at, datetime.datetime):
        created_at = created_at.strftime("%d-%b-%Y")

    base_dir = os.path.dirname(os.path.dirname(__file__))
    cards_dir = os.path.join(base_dir, "static", "uploads", "cards")
    os.makedirs(cards_dir, exist_ok=True)

    pdf_filename = f"donor_card_{donor_id}.pdf"
    pdf_path = os.path.join(cards_dir, pdf_filename)

    # Ensure QR Code exists
    qr_web_url, qr_fs_path = generate_donor_qr(donor_id)

    # Setup standard card dimensions on canvas (Card size: 420 x 260 pt)
    card_w = 420
    card_h = 260

    c = canvas.Canvas(pdf_path, pagesize=(card_w, card_h))

    # 1. Background styling
    c.setFillColor(colors.HexColor("#F8FAFC"))
    c.rect(0, 0, card_w, card_h, fill=1, stroke=0)

    # 2. Header Banner (Deep Navy)
    c.setFillColor(colors.HexColor("#1D3557"))
    c.rect(0, card_h - 60, card_w, 60, fill=1, stroke=0)

    # Header Accent line (Crimson)
    c.setFillColor(colors.HexColor("#E63946"))
    c.rect(0, card_h - 63, card_w, 3, fill=1, stroke=0)

    # Title & Subtitle in Header
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(16, card_h - 26, "ORGAN & BLOOD DONATION CARD")
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(colors.HexColor("#A8DADC"))
    c.drawString(16, card_h - 42, "GOVERNMENT RECOGNIZED LIFE SAVER PLEDGE")

    # Blood Group Badge in top right
    c.setFillColor(colors.HexColor("#E63946"))
    c.roundRect(card_w - 75, card_h - 48, 60, 36, 6, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(card_w - 45, card_h - 32, blood_group)
    c.setFont("Helvetica", 6)
    c.drawCentredString(card_w - 45, card_h - 44, "BLOOD GROUP")

    # 3. Donor Photo / Avatar box (Left)
    photo_x = 16
    photo_y = card_h - 165
    photo_w = 85
    photo_h = 95

    # Check if custom photo exists
    photo_url = donor_data.get("photo_url", "")
    has_custom_photo = False
    if photo_url and not photo_url.endswith("default-avatar.png"):
        photo_rel = photo_url.lstrip("/")
        photo_abs = os.path.join(base_dir, photo_rel)
        if os.path.exists(photo_abs):
            try:
                c.drawImage(photo_abs, photo_x, photo_y, width=photo_w, height=photo_h, preserveAspectRatio=True)
                has_custom_photo = True
            except Exception:
                has_custom_photo = False

    if not has_custom_photo:
        c.setFillColor(colors.HexColor("#E2E8F0"))
        c.roundRect(photo_x, photo_y, photo_w, photo_h, 4, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#457B9D"))
        c.setFont("Helvetica-Bold", 28)
        c.drawCentredString(photo_x + photo_w / 2, photo_y + photo_h / 2 - 8, "♥")
        c.setFont("Helvetica", 7)
        c.drawCentredString(photo_x + photo_w / 2, photo_y + 12, "DONOR")

    # Photo border
    c.setStrokeColor(colors.HexColor("#CBD5E1"))
    c.setLineWidth(1)
    c.roundRect(photo_x, photo_y, photo_w, photo_h, 4, fill=0, stroke=1)

    # 4. Donor Details (Middle column)
    info_x = 112
    c.setFillColor(colors.HexColor("#64748B"))
    c.setFont("Helvetica-Bold", 7)
    c.drawString(info_x, card_h - 78, "DONOR NAME")
    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 10.5)
    c.drawString(info_x, card_h - 91, full_name[:26])

    c.setFillColor(colors.HexColor("#64748B"))
    c.setFont("Helvetica-Bold", 7)
    c.drawString(info_x, card_h - 105, "UNIQUE DONOR ID")
    c.setFillColor(colors.HexColor("#1D3557"))
    c.setFont("Helvetica-Bold", 10)
    c.drawString(info_x, card_h - 118, donor_id)

    c.setFillColor(colors.HexColor("#64748B"))
    c.setFont("Helvetica-Bold", 7)
    c.drawString(info_x, card_h - 132, "PLEDGED ORGANS")
    c.setFillColor(colors.HexColor("#E63946"))
    c.setFont("Helvetica-Bold", 8.5)
    if len(organ_type) > 26:
        parts = [p.strip() for p in organ_type.split(",")]
        mid = (len(parts) + 1) // 2
        line1 = ", ".join(parts[:mid])
        line2 = ", ".join(parts[mid:])
        c.drawString(info_x, card_h - 143, line1)
        c.drawString(info_x, card_h - 153, line2)
        loc_y = card_h - 168
    else:
        c.drawString(info_x, card_h - 144, organ_type)
        loc_y = card_h - 162

    c.setFillColor(colors.HexColor("#64748B"))
    c.setFont("Helvetica-Bold", 7)
    c.drawString(info_x, loc_y, "CITY / LOCATION")
    c.setFillColor(colors.HexColor("#1E293B"))
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(info_x, loc_y - 12, f"{city}, Tamil Nadu")

    # 5. QR Code on right side
    qr_x = card_w - 95
    qr_y = card_h - 175
    qr_size = 80
    if os.path.exists(qr_fs_path):
        c.drawImage(qr_fs_path, qr_x, qr_y, width=qr_size, height=qr_size)
        c.setFillColor(colors.HexColor("#64748B"))
        c.setFont("Helvetica", 6)
        c.drawCentredString(qr_x + qr_size / 2, qr_y - 8, "SCAN TO VERIFY")

    # 6. Card Footer Banner
    c.setFillColor(colors.HexColor("#F1F5F9"))
    c.rect(0, 0, card_w, 42, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#E2E8F0"))
    c.line(0, 42, card_w, 42)

    # Verification Badge Pill
    c.setFillColor(colors.HexColor("#2A9D8F"))
    c.roundRect(16, 12, 90, 20, 10, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(16 + 45, 18, f"STATUS: {status.upper()}")

    # Date info
    c.setFillColor(colors.HexColor("#64748B"))
    c.setFont("Helvetica", 8)
    c.drawString(116, 20, f"Issued: {created_at}")

    # Official Helpline / Emergency Note
    c.setFont("Helvetica-Bold", 7)
    c.setFillColor(colors.HexColor("#1D3557"))
    c.drawRightString(card_w - 16, 20, "24x7 Emergency: 108 / 104")

    # Save & finalize PDF
    c.showPage()
    c.save()

    web_pdf_url = f"/static/uploads/cards/{pdf_filename}"
    return web_pdf_url, pdf_path
