from decimal import Decimal
from io import BytesIO
from urllib.parse import urlencode
from uuid import uuid4

import qrcode
from flask import Blueprint, current_app, flash, redirect, render_template, url_for
from flask import send_file
from flask_login import current_user

from ..cart.routes import _get_cart, cart_totals
from ..extensions import db
from ..models import Order, OrderItem, Payment, ProductVariant
from ..notifications import send_order_status_email
from .forms import CheckoutForm, PaymentForm


checkout_bp = Blueprint("checkout", __name__, url_prefix="/checkout")


def _order_number():
    return f"COORG-{uuid4().hex[:10].upper()}"


@checkout_bp.route("/", methods=["GET", "POST"])
def checkout():
    cart = _get_cart(create=False)
    if not cart or not cart.items:
        flash("Your cart is empty.", "error")
        return redirect(url_for("cart.view_cart"))
    form = CheckoutForm()
    totals = cart_totals(cart)
    if form.validate_on_submit():
        try:
            subtotal = Decimal("0.00")
            order = Order(
                order_number=_order_number(),
                user_id=current_user.id if current_user.is_authenticated else None,
                customer_name=form.customer_name.data.strip(),
                email=form.email.data.strip().lower(),
                phone=form.phone.data.strip(),
                address_line=form.address_line.data.strip(),
                city=form.city.data.strip(),
                state=form.state.data.strip(),
                postal_code=form.postal_code.data.strip(),
                subtotal=Decimal("0.00"),
                shipping_cost=Decimal("0.00"),
                total_amount=Decimal("0.00"),
                payment_status="pending_verification",
                order_status="pending",
            )
            db.session.add(order)
            db.session.flush()
            for item in list(cart.items):
                variant = (
                    db.session.query(ProductVariant)
                    .filter_by(id=item.variant_id, is_active=True)
                    .with_for_update()
                    .first()
                )
                if not variant or not variant.product.is_active or item.quantity > variant.stock_quantity:
                    raise ValueError(f"{item.variant.label} is no longer available in the requested quantity.")
                line_total = variant.price * item.quantity
                subtotal += line_total
                variant.stock_quantity -= item.quantity
                db.session.add(
                    OrderItem(
                        order=order,
                        variant=variant,
                        product_name=variant.product.name,
                        variant_label=variant.label,
                        sku=variant.sku,
                        unit_price=variant.price,
                        quantity=item.quantity,
                        line_total=line_total,
                    )
                )
            order.subtotal = subtotal
            order.shipping_cost = Decimal("0.00")
            order.total_amount = subtotal
            db.session.add(Payment(order=order, payment_method="upi_qr", payment_status="pending_verification"))
            db.session.delete(cart)
            db.session.commit()
        except ValueError as error:
            db.session.rollback()
            flash(str(error), "error")
            return redirect(url_for("cart.view_cart"))
        return redirect(url_for("checkout.payment", order_number=order.order_number))
    return render_template("checkout/checkout.html", form=form, cart=cart, totals=totals)


@checkout_bp.route("/payment/<order_number>", methods=["GET", "POST"])
def payment(order_number):
    order = Order.query.filter_by(order_number=order_number).first_or_404()
    payment_record = order.payments[-1] if order.payments else None
    form = PaymentForm()
    if form.validate_on_submit():
        if payment_record and payment_record.payment_status == "pending_verification":
            is_first_reference = not payment_record.transaction_reference
            payment_record.transaction_reference = form.transaction_reference.data.strip()
            db.session.commit()
            if is_first_reference:
                send_order_status_email(order)
            flash("Payment reference submitted. An administrator will verify it before confirmation.", "success")
        return redirect(url_for("checkout.order_confirmation", order_number=order.order_number))
    return render_template(
        "checkout/payment.html",
        form=form,
        order=order,
        payment_record=payment_record,
        upi_id=current_app.config["UPI_ID"],
    )


@checkout_bp.get("/qr/<order_number>")
def payment_qr(order_number):
    order = Order.query.filter_by(order_number=order_number).first_or_404()
    payload = "upi://pay?" + urlencode(
        {
            "pa": current_app.config["UPI_ID"],
            "pn": current_app.config["BRAND_NAME"],
            "am": f"{order.total_amount:.2f}",
            "cu": "INR",
            "tn": order.order_number,
        }
    )
    image = qrcode.make(payload)
    stream = BytesIO()
    image.save(stream, format="PNG")
    stream.seek(0)
    return send_file(stream, mimetype="image/png", max_age=300)


@checkout_bp.get("/order/<order_number>")
def order_confirmation(order_number):
    order = Order.query.filter_by(order_number=order_number).first_or_404()
    return render_template("checkout/confirmation.html", order=order)
