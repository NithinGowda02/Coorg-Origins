from datetime import datetime, timezone

from ..extensions import db


class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    payment_method = db.Column(db.String(30), nullable=False, default="upi_qr")
    transaction_reference = db.Column(db.String(120), nullable=True, index=True)
    payment_status = db.Column(db.String(40), nullable=False, default="pending_verification", index=True)
    payment_screenshot_url = db.Column(db.String(500), nullable=True)
    verified_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    verified_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    order = db.relationship("Order", back_populates="payments")
    verifier = db.relationship("User", foreign_keys=[verified_by])
