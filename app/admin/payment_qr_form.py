from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired


class PaymentQrForm(FlaskForm):
    image = FileField(
        "Payment QR image",
        validators=[
            FileRequired(),
            FileAllowed(["png", "jpg", "jpeg", "webp"], "Use a PNG, JPG, or WebP image."),
        ],
    )