import re

from app.extensions import db
from app.models import Category, Order, Product, ProductVariant


def test_guest_checkout_reduces_stock_and_creates_pending_payment(client, app, monkeypatch):
    with app.app_context():
        category = Category(name="Coffee", slug="coffee")
        product = Product(name="Coorg Coffee", slug="coorg-coffee", category=category)
        db.session.add_all([category, product])
        db.session.flush()
        variant = ProductVariant(product=product, sku="COFFEE-250", label="250g", quantity_value=250, quantity_unit="g", price=300, stock_quantity=5)
        db.session.add(variant)
        db.session.commit()
        variant_id = variant.id

    notifications = []
    monkeypatch.setattr(
        "app.checkout.routes.send_order_status_email",
        lambda order: notifications.append((order.email, order.order_status)),
    )
    app.config["WTF_CSRF_ENABLED"] = True
    product_page = client.get("/product/coorg-coffee")
    product_token = re.search(rb'<input[^>]*name="csrf_token"[^>]*value="([^"]+)"', product_page.data).group(1).decode()
    assert client.post(f"/cart/add/{variant_id}", data={"csrf_token": product_token}).status_code == 302
    with app.app_context():
        item_id = db.session.get(ProductVariant, variant_id).cart_items[0].id
    cart_page = client.get("/cart/")
    cart_token = re.search(rb'<input[^>]*name="csrf_token"[^>]*value="([^"]+)"', cart_page.data).group(1).decode()
    assert client.post(
        f"/cart/item/{item_id}/update",
        data={"csrf_token": cart_token, "quantity": 2},
    ).status_code == 302
    checkout_page = client.get("/checkout/")
    checkout_token = re.search(rb'<input[^>]*name="csrf_token"[^>]*value="([^"]+)"', checkout_page.data).group(1).decode()
    response = client.post(
        "/checkout/",
        data={
            "csrf_token": checkout_token,
            "customer_name": "Asha Rao",
            "email": "asha@example.com",
            "phone": "9876543210",
            "address_line": "Hill Road",
            "city": "Madikeri",
            "state": "Karnataka",
            "postal_code": "571201",
        },
    )
    assert response.status_code == 302
    with app.app_context():
        order = Order.query.one()
        assert order.total_amount == 600
        assert order.payment_status == "pending_verification"
        assert db.session.get(ProductVariant, variant_id).stock_quantity == 3
    assert notifications == [("asha@example.com", "pending")]

    stale_update = client.post(
        f"/cart/item/{item_id}/update",
        data={"csrf_token": cart_token, "quantity": 2},
        follow_redirects=True,
    )
    assert stale_update.status_code == 200
    assert b"That cart item is no longer available." in stale_update.data

    stale_remove = client.post(
        f"/cart/item/{item_id}/remove",
        data={"csrf_token": cart_token},
        follow_redirects=True,
    )
    assert stale_remove.status_code == 200
    assert b"That cart item is no longer available." in stale_remove.data
