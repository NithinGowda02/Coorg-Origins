from types import SimpleNamespace
from unittest.mock import patch

from app.notifications import send_order_status_email


def test_order_status_email_uses_configured_smtp(app):
    sent_messages = []

    class FakeSMTP:
        def __init__(self, server, port, timeout):
            assert (server, port, timeout) == ("smtp.example.com", 587, 10)

        def __enter__(self):
            return self

        def __exit__(self, exception_type, exception, traceback):
            return False

        def starttls(self):
            pass

        def login(self, username, password):
            assert (username, password) == ("smtp-user", "smtp-secret")

        def send_message(self, message):
            sent_messages.append(message)

    app.config.update(
        MAIL_SERVER="smtp.example.com",
        MAIL_PORT=587,
        MAIL_USE_TLS=True,
        MAIL_USERNAME="smtp-user",
        MAIL_PASSWORD="smtp-secret",
        MAIL_DEFAULT_SENDER="orders@example.com",
    )
    order = SimpleNamespace(
        email="asha@example.com",
        customer_name="Asha Rao",
        order_number="COORG-EMAIL-TEST",
        order_status="rejected",
        total_amount="300.00",
    )

    with app.app_context(), patch("app.notifications.smtplib.SMTP", FakeSMTP):
        assert send_order_status_email(order) is True

    assert len(sent_messages) == 1
    message = sent_messages[0]
    assert message["To"] == "asha@example.com"
    assert message["From"] == "orders@example.com"
    assert message["Subject"] == "Order COORG-EMAIL-TEST: Rejected"
    assert "could not confirm your order" in message.get_content()
    assert "check the payment details" in message.get_content()


def test_order_status_email_has_status_specific_customer_copy(app):
    sent_messages = []

    class FakeSMTP:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exception_type, exception, traceback):
            return False

        def starttls(self):
            pass

        def send_message(self, message):
            sent_messages.append(message)

    app.config.update(
        MAIL_SERVER="smtp.example.com",
        MAIL_PORT=587,
        MAIL_USE_TLS=True,
        MAIL_USERNAME=None,
        MAIL_PASSWORD=None,
        MAIL_DEFAULT_SENDER="orders@example.com",
    )
    order = SimpleNamespace(
        email="asha@example.com",
        customer_name="Asha Rao",
        order_number="COORG-EMAIL-TEST",
        order_status="pending",
        total_amount="300.00",
    )

    with app.app_context(), patch("app.notifications.smtplib.SMTP", FakeSMTP):
        assert send_order_status_email(order) is True
        order.order_status = "confirmed"
        assert send_order_status_email(order) is True

    pending_content = sent_messages[0].get_content()
    confirmed_content = sent_messages[1].get_content()
    assert "reviewing the details" in pending_content
    assert "within 24 hours" in pending_content
    assert "It is confirmed" in confirmed_content
    assert "within 24 hours" in confirmed_content
    assert pending_content != confirmed_content