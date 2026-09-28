from decimal import Decimal
from uuid import uuid4

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user

from ..extensions import db
from ..models import Cart, CartItem, ProductVariant


cart_bp = Blueprint("cart", __name__, url_prefix="/cart")


def _get_cart(create=True):
    session_id = session.get("cart_session_id")
    if not session_id and create:
        session_id = uuid4().hex
        session["cart_session_id"] = session_id
    cart = Cart.query.filter_by(session_id=session_id).first() if session_id else None
    if not cart and create:
        cart = Cart(session_id=session_id, user_id=current_user.id if current_user.is_authenticated else None)
        db.session.add(cart)
        db.session.flush()
    return cart


def cart_totals(cart):
    subtotal = sum((item.variant.price * item.quantity for item in cart.items), Decimal("0.00"))
    return {"subtotal": subtotal, "shipping": Decimal("0.00"), "total": subtotal}


@cart_bp.get("/")
def view_cart():
    cart = _get_cart()
    return render_template("cart/cart.html", cart=cart, totals=cart_totals(cart))


@cart_bp.post("/add/<int:variant_id>")
def add_to_cart(variant_id):
    variant = db.get_or_404(ProductVariant, variant_id)
    if not variant.is_active or not variant.product.is_active or variant.stock_quantity < 1:
        flash("That variant is currently unavailable.", "error")
        return redirect(url_for("main.product_detail", slug=variant.product.slug))
    cart = _get_cart()
    quantity = 1
    item = CartItem.query.filter_by(cart_id=cart.id, variant_id=variant.id).first()
    if item:
        quantity = item.quantity + 1
    if quantity > variant.stock_quantity:
        flash(f"Only {variant.stock_quantity} available.", "error")
    elif item:
        item.quantity = quantity
        db.session.commit()
        flash("Cart updated.", "success")
    else:
        db.session.add(CartItem(cart=cart, variant=variant, quantity=1))
        db.session.commit()
        flash("Added to cart.", "success")
    return redirect(url_for("cart.view_cart"))


@cart_bp.post("/item/<int:item_id>/update")
def update_item(item_id):
    cart = _get_cart()
    item = CartItem.query.filter_by(cart_id=cart.id, id=item_id).first()
    if not item:
        flash("That cart item is no longer available. Your cart has been refreshed.", "error")
        return redirect(url_for("cart.view_cart"))
    quantity = max(0, int(request.form.get("quantity", 1)))
    if quantity > item.variant.stock_quantity:
        flash(f"Only {item.variant.stock_quantity} available.", "error")
    elif quantity == 0:
        db.session.delete(item)
        db.session.commit()
        flash("Item removed.", "success")
    else:
        item.quantity = quantity
        db.session.commit()
        flash("Cart updated.", "success")
    return redirect(url_for("cart.view_cart"))


@cart_bp.post("/item/<int:item_id>/remove")
def remove_item(item_id):
    cart = _get_cart()
    item = CartItem.query.filter_by(cart_id=cart.id, id=item_id).first()
    if not item:
        flash("That cart item is no longer available. Your cart has been refreshed.", "error")
        return redirect(url_for("cart.view_cart"))
    db.session.delete(item)
    db.session.commit()
    flash("Item removed.", "success")
    return redirect(url_for("cart.view_cart"))
