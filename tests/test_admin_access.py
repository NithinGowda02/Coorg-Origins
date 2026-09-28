from app.extensions import db
from app.models import Cart, CartItem, Category, Order, OrderItem, Payment, Product, ProductVariant, User


def test_admin_orders_require_admin_login(client, app):
    assert client.get("/admin/orders").status_code == 302
    with app.app_context():
        admin = User(name="Admin", email="admin@example.com", role="admin")
        admin.set_password("correct-password")
        db.session.add(admin)
        db.session.commit()
    assert client.post("/auth/login", data={"email": "admin@example.com", "password": "correct-password"}).status_code == 302
    assert client.get("/admin/orders").status_code == 200


def test_category_admin_screen_is_removed_from_admin_workspace(client, app):
    with app.app_context():
        admin = User(name="Admin", email="admin@example.com", role="admin")
        admin.set_password("correct-password")
        db.session.add(admin)
        db.session.commit()

    client.post("/auth/login", data={"email": "admin@example.com", "password": "correct-password"})

    assert client.get("/admin/categories").status_code == 404
    dashboard = client.get("/admin/")
    assert dashboard.status_code == 200
    assert b"href=\"/admin/categories\"" not in dashboard.data


def test_order_status_update_persists_and_notifies_customer(client, app, monkeypatch):
    with app.app_context():
        admin = User(name="Admin", email="admin@example.com", role="admin")
        admin.set_password("correct-password")
        order = Order(
            order_number="COORG-STATUS-TEST",
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
            order_status="confirmed",
        )
        db.session.add_all([admin, order])
        db.session.commit()
        order_id = order.id

    notifications = []
    monkeypatch.setattr(
        "app.admin.routes.send_order_status_email",
        lambda order: notifications.append((order.email, order.order_status)) or True,
    )
    client.post("/auth/login", data={"email": "admin@example.com", "password": "correct-password"})
    response = client.post(
        f"/admin/orders/{order_id}",
        data={"order_status": "rejected", "submit": "Update status"},
    )

    assert response.status_code == 302
    with app.app_context():
        assert db.session.get(Order, order_id).order_status == "rejected"
    assert notifications == [("asha@example.com", "rejected")]

    client.post(
        f"/admin/orders/{order_id}",
        data={"order_status": "rejected", "submit": "Update status"},
    )
    assert notifications == [("asha@example.com", "rejected")]


def test_failed_order_status_email_is_reported(client, app, monkeypatch):
    with app.app_context():
        admin = User(name="Admin", email="admin@example.com", role="admin")
        admin.set_password("correct-password")
        order = Order(
            order_number="COORG-MAIL-FAIL",
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
            order_status="pending",
        )
        db.session.add_all([admin, order])
        db.session.commit()
        order_id = order.id

    monkeypatch.setattr("app.admin.routes.send_order_status_email", lambda order: False)
    client.post("/auth/login", data={"email": "admin@example.com", "password": "correct-password"})
    response = client.post(
        f"/admin/orders/{order_id}",
        data={"order_status": "confirmed", "submit": "Update status"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"the customer email could not be sent" in response.data
    with app.app_context():
        assert db.session.get(Order, order_id).order_status == "confirmed"


def test_product_form_renders_required_variant_label(client, app):
    with app.app_context():
        admin = User(name="Admin", email="admin@example.com", role="admin")
        admin.set_password("correct-password")
        category = Category(name="Coorg Organic Spices", slug="coorg-organic-spices")
        db.session.add_all([admin, category])
        db.session.commit()

    client.post("/auth/login", data={"email": "admin@example.com", "password": "correct-password"})
    response = client.get("/admin/products/new")

    assert response.status_code == 200
    assert b'id="variants-0-label"' in response.data
    assert b'name="category_id"' in response.data
    category_select = response.data.split(b'<select id="category_id"', 1)[1].split(b'</select>', 1)[0]
    assert b"Coorg Organic Spices" in category_select
    assert b"Coorg Masala Powders" in category_select


def test_new_product_is_saved_under_selected_category(client, app):
    with app.app_context():
        admin = User(name="Admin", email="admin@example.com", role="admin")
        admin.set_password("correct-password")
        coffee = Category(name="Coffee", slug="coffee")
        spices = Category(name="Coorg Organic Spices", slug="coorg-organic-spices")
        db.session.add_all([admin, coffee, spices])
        db.session.commit()
        spices_id = spices.id

    client.post("/auth/login", data={"email": "admin@example.com", "password": "correct-password"})
    response = client.post(
        "/admin/products/new",
        data={
            "name": "Coorg Black Pepper",
            "category_id": str(spices_id),
            "variants-0-label": "100g",
            "variants-0-quantity_value": "100",
            "variants-0-quantity_unit": "g",
            "variants-0-price": "160",
            "variants-0-stock_quantity": "5",
        },
    )

    assert response.status_code == 302
    with app.app_context():
        product = Product.query.filter_by(slug="coorg-black-pepper").one()
        assert product.category_id == spices_id


def test_duplicate_product_name_shows_validation_error(client, app):
    with app.app_context():
        admin = User(name="Admin", email="admin@example.com", role="admin")
        admin.set_password("correct-password")
        category = Category(name="Coffee", slug="coffee")
        db.session.add_all([admin, category])
        db.session.flush()
        db.session.add(Product(name="Coorg Coffee", slug="coorg-coffee", category=category))
        db.session.commit()

    client.post("/auth/login", data={"email": "admin@example.com", "password": "correct-password"})
    response = client.post(
        "/admin/products/new",
        data={
            "name": "Coorg Coffee",
            "variants-0-label": "250g",
            "variants-0-quantity_value": "250",
            "variants-0-quantity_unit": "g",
            "variants-0-price": "300",
            "variants-0-stock_quantity": "5",
        },
    )

    assert response.status_code == 200
    assert b"A product with that name already exists." in response.data


def test_invalid_product_variant_shows_validation_error(client, app):
    with app.app_context():
        admin = User(name="Admin", email="admin@example.com", role="admin")
        admin.set_password("correct-password")
        db.session.add(admin)
        db.session.commit()

    client.post("/auth/login", data={"email": "admin@example.com", "password": "correct-password"})
    response = client.post(
        "/admin/products/new",
        data={
            "name": "Coorg Coffee",
            "variants-0-label": "250g",
            "variants-0-quantity_value": "250",
            "variants-0-quantity_unit": "g",
            "variants-0-price": "-10",
            "variants-0-stock_quantity": "5",
        },
    )

    assert response.status_code == 200
    assert b"Number must be at least 0." in response.data


def test_edit_product_can_add_variant_without_reinserting_existing_one(client, app):
    with app.app_context():
        admin = User(name="Admin", email="admin@example.com", role="admin")
        admin.set_password("correct-password")
        category = Category(name="Pepper", slug="pepper")
        product = Product(name="Coorg Pepper", slug="coorg-pepper", category=category)
        existing_variant = ProductVariant(
            product=product,
            sku="COORG-PEPPER-250G",
            label="250g",
            quantity_value=250,
            quantity_unit="g",
            price=200,
            stock_quantity=8,
        )
        db.session.add_all([admin, category, product, existing_variant])
        db.session.commit()
        product_id = product.id
        variant_id = existing_variant.id

    client.post("/auth/login", data={"email": "admin@example.com", "password": "correct-password"})
    edit_page = client.get(f"/admin/products/{product_id}/edit")
    assert f'name="variants-0-id" type="hidden" value="{variant_id}"'.encode() in edit_page.data

    response = client.post(
        f"/admin/products/{product_id}/edit",
        data={
            "name": "Coorg Pepper",
            "is_active": "y",
            "variants-0-id": str(variant_id),
            "variants-0-label": "250g",
            "variants-0-quantity_value": "250",
            "variants-0-quantity_unit": "g",
            "variants-0-price": "200",
            "variants-0-stock_quantity": "8",
            "variants-0-is_active": "y",
            "variants-1-id": "",
            "variants-1-label": "500g",
            "variants-1-quantity_value": "500",
            "variants-1-quantity_unit": "g",
            "variants-1-price": "350",
            "variants-1-stock_quantity": "6",
            "variants-1-is_active": "y",
        },
    )

    assert response.status_code == 302
    with app.app_context():
        variants = ProductVariant.query.filter_by(product_id=product_id).order_by(ProductVariant.id).all()
        assert [(variant.id, variant.label, variant.stock_quantity) for variant in variants] == [
            (variant_id, "250g", 8),
            (variants[1].id, "500g", 6),
        ]


def test_admin_can_delete_product_without_erasing_order_history(client, app):
    with app.app_context():
        admin = User(name="Admin", email="admin@example.com", role="admin")
        admin.set_password("correct-password")
        category = Category(name="Coffee", slug="coffee")
        product = Product(name="Coorg Coffee", slug="coorg-coffee", category=category)
        variant = ProductVariant(
            product=product, sku="COFFEE-DELETE-250", label="250g",
            quantity_value=250, quantity_unit="g", price=300, stock_quantity=4,
        )
        cart = Cart(session_id="cart-product-delete")
        cart_item = CartItem(cart=cart, variant=variant, quantity=1)
        order = Order(
            order_number="COORG-DELETE-PRODUCT", customer_name="Asha Rao",
            email="asha@example.com", phone="9876543210", address_line="Hill Road",
            city="Madikeri", state="Karnataka", postal_code="571201",
            subtotal=300, shipping_cost=0, total_amount=300,
        )
        order_item = OrderItem(
            order=order, variant=variant, product_name=product.name, variant_label="250g",
            sku=variant.sku, unit_price=300, quantity=1, line_total=300,
        )
        db.session.add_all([admin, category, product, variant, cart, cart_item, order, order_item])
        db.session.commit()
        product_id = product.id
        cart_item_id = cart_item.id
        order_item_id = order_item.id

    client.post("/auth/login", data={"email": "admin@example.com", "password": "correct-password"})
    response = client.post(f"/admin/products/{product_id}/delete", data={"csrf_token": "test"})

    assert response.status_code == 302
    with app.app_context():
        assert db.session.get(Product, product_id) is None
        assert db.session.get(CartItem, cart_item_id) is None
        historical_item = db.session.get(OrderItem, order_item_id)
        assert historical_item.product_name == "Coorg Coffee"
        assert historical_item.variant_id is None


def test_admin_can_delete_order_and_its_payment_records(client, app):
    with app.app_context():
        admin = User(name="Admin", email="admin@example.com", role="admin")
        admin.set_password("correct-password")
        order = Order(
            order_number="COORG-DELETE-ORDER", customer_name="Asha Rao",
            email="asha@example.com", phone="9876543210", address_line="Hill Road",
            city="Madikeri", state="Karnataka", postal_code="571201",
            subtotal=300, shipping_cost=0, total_amount=300,
        )
        payment = Payment(order=order, payment_method="upi_qr")
        order_item = OrderItem(
            order=order, product_name="Coffee", variant_label="250g", sku="COFFEE-250",
            unit_price=300, quantity=1, line_total=300,
        )
        db.session.add_all([admin, order, payment, order_item])
        db.session.commit()
        order_id = order.id
        payment_id = payment.id
        order_item_id = order_item.id

    client.post("/auth/login", data={"email": "admin@example.com", "password": "correct-password"})
    response = client.post(f"/admin/orders/{order_id}/delete", data={"csrf_token": "test"})

    assert response.status_code == 302
    with app.app_context():
        assert db.session.get(Order, order_id) is None
        assert db.session.get(Payment, payment_id) is None
        assert db.session.get(OrderItem, order_item_id) is None
