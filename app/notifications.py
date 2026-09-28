import logging
import smtplib
from email.message import EmailMessage

from flask import current_app


logger = logging.getLogger(__name__)


def send_order_status_email(order):
    if not any(payment.transaction_reference for payment in order.payments):
        logger.info("Order status email deferred until a payment reference is submitted for %s.", order.order_number)
        return False

    config = current_app.config
    mail_server = config.get("MAIL_SERVER")
    sender = config.get("MAIL_DEFAULT_SENDER")
    if not mail_server or not sender:
        logger.warning("Order status email skipped: configure MAIL_SERVER and MAIL_DEFAULT_SENDER.")
        return False

    status = order.order_status.replace("_", " ").title()
    status_message = {
        "pending": (
            "Thank you for placing your order with us. We have received it, and our team is "
            "reviewing the details. We will contact you within 24 hours with an update."
        ),
        "confirmed": (
            "Thank you for your order. It is confirmed, and our team will contact you within "
            "24 hours with the next steps."
        ),
        "processing": (
            "Your order is now being prepared. We will email you again when it has been dispatched."
        ),
        "shipped": (
            "Your order has been shipped and is on its way. We will send you another update "
            "when it has been delivered."
        ),
        "delivered": (
            "Your order is marked as delivered. We hope you enjoy it. If anything is missing "
            "or not right, reply to this email and our team will be happy to help."
        ),
        "rejected": (
            "We are sorry, but we could not confirm your order. Please check the payment details "
            "and transaction reference you submitted. If you believe this is a mistake or need "
            "help, reply to this email and our team will assist you."
        ),
        "cancelled": (
            "Your order has been cancelled. If you did not request this or have any questions, "
            "reply to this email and our team will help."
        ),
    }.get(order.order_status, f"The status of your order is now {status}.")
    message = EmailMessage()
    message["Subject"] = f"Order {order.order_number}: {status}"
    message["From"] = sender
    message["To"] = order.email
    message.set_content(
        f"Hello {order.customer_name},\n\n"
        f"{status_message}\n\n"
        f"Order number: {order.order_number}\n"
        f"Order status: {status}\n"
        f"Order total: Rs. {order.total_amount}\n\n"
        f"For questions, please reply to this email.\n\n"
        f"{config['BRAND_NAME']}"
    )

    try:
        with smtplib.SMTP(mail_server, config["MAIL_PORT"], timeout=10) as smtp:
            if config["MAIL_USE_TLS"]:
                smtp.starttls()
            username = config.get("MAIL_USERNAME")
            password = config.get("MAIL_PASSWORD")
            if username:
                smtp.login(username, password or "")
            smtp.send_message(message)
    except Exception:
        logger.exception("Could not send order status email for %s.", order.order_number)
        return False
    return True
