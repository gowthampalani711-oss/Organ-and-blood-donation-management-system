import os
import qrcode
from dotenv import load_dotenv

load_dotenv()
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:5000")


def generate_donor_qr(donor_id):
    """
    Generates a secure QR code image containing verification URL for the donor.
    Returns relative web path to saved QR PNG file.
    """
    verification_url = f"{APP_BASE_URL}/verify-donor/{donor_id}"

    upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "uploads", "qrcodes")
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, f"qr_{donor_id}.png")

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=2,
    )
    qr.add_data(verification_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#1D3557", back_color="white")
    img.save(file_path)

    return f"/static/uploads/qrcodes/qr_{donor_id}.png", file_path
