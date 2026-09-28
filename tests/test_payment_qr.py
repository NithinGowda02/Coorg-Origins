from io import BytesIO
from urllib.parse import parse_qs, urlparse

from PIL import Image
import qrcode as qrcode_lib

from app.extensions import db
from app.models import Order, User


def test_admin_upload_payment_qr_and_customer_payment_uses_dynamic_amount_qr(client, app, tmp_path, monkeypatch):
    assert client.get("/admin/payment-qr").status_code == 302

    with app.app_context():
        admin = User(name="Admin", email="admin@example.com", role="admin")
        admin.set_password("correct-password")
        order = Order(
            order_number="COORG-QR-TEST",
            customer_name="Asha Rao",
            email="asha@example.com",
            phone="9876543210",
            address_line="Hill Road",
            city="Madikeri",
            state="Karnataka",
            postal_code="571201",
            subtotal=300,
            shipping_cost=0,
            total_amount=300,
        )
        db.session.add_all([admin, order])
        db.session.commit()

    static_folder = tmp_path / "static"
    qr_path = static_folder / "uploads" / "payment" / "payment-qr.png"
    app.static_folder = str(static_folder)
    app.config["PAYMENT_QR_PATH"] = qr_path
    client.post("/auth/login", data={"email": "admin@example.com", "password": "correct-password"})

    image_bytes = BytesIO()
    Image.new("RGB", (128, 128), "white").save(image_bytes, format="PNG")
    image_bytes.seek(0)
    upload_response = client.post(
        "/admin/payment-qr",
        data={"image": (image_bytes, "merchant-qr.png")},
        follow_redirects=True,
    )

    assert upload_response.status_code == 200
    assert b"Payment QR image updated." in upload_response.data
    assert qr_path.is_file()

    payment_response = client.get("/checkout/payment/COORG-QR-TEST")
    assert payment_response.status_code == 200
    assert b"/checkout/qr/COORG-QR-TEST" in payment_response.data
    assert b"300.00" in payment_response.data
    assert client.get("/static/uploads/payment/payment-qr.png").status_code == 200

    payloads = []
    original_make = qrcode_lib.make

    def capture_payload(payload):
        payloads.append(payload)
        return original_make(payload)

    monkeypatch.setattr("app.checkout.routes.qrcode.make", capture_payload)
    qr_response = client.get("/checkout/qr/COORG-QR-TEST")

    assert qr_response.status_code == 200
    assert qr_response.mimetype == "image/png"
    query = parse_qs(urlparse(payloads[0]).query)
    assert query["pa"] == [app.config["UPI_ID"]]
    assert query["am"] == ["300.00"]
    assert query["cu"] == ["INR"]
    assert query["tn"] == ["COORG-QR-TEST"]