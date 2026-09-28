from app.extensions import db
from app.models import Category, Product, ProductVariant


def test_public_catalog_and_seo_routes(client, app):
    with app.app_context():
        category = Category(name="Coffee", slug="coffee")
        product = Product(name="Coorg Coffee", slug="coorg-coffee", category=category, is_featured=True)
        db.session.add_all([category, product])
        db.session.flush()
        db.session.add(ProductVariant(product=product, sku="COFFEE-250", label="250g", quantity_value=250, quantity_unit="g", price=300, stock_quantity=4))
        db.session.commit()

    assert client.get("/").status_code == 200
    assert client.get("/shop").status_code == 200
    assert client.get("/product/coorg-coffee").status_code == 200
    assert client.get("/sitemap.xml").status_code == 200
    assert b"coorg-coffee" in client.get("/sitemap.xml").data
    assert b"Disallow: /admin/" in client.get("/robots.txt").data
    assert client.get("/missing-page").status_code == 404


def test_category_navigation_and_search_filter_catalog(client, app):
    with app.app_context():
        coffee = Category(name="Coffee Powder", slug="coffee-powder")
        spices = Category(name="Coorg Organic Spices", slug="coorg-organic-spices")
        coffee_product = Product(
            name="Arabica Coffee",
            slug="arabica-coffee",
            category=coffee,
            description="Whole bean coffee from the hills.",
        )
        spice_product = Product(
            name="Black Pepper",
            slug="black-pepper",
            category=spices,
            description="A warming spice for everyday cooking.",
        )
        db.session.add_all([coffee, spices, coffee_product, spice_product])
        db.session.flush()
        db.session.add_all([
            ProductVariant(product=coffee_product, sku="ARABICA-250", label="250g", quantity_value=250, quantity_unit="g", price=300, stock_quantity=4),
            ProductVariant(product=spice_product, sku="PEPPER-100", label="100g", quantity_value=100, quantity_unit="g", price=160, stock_quantity=5),
        ])
        db.session.commit()

    home = client.get("/")
    assert b"/category/coorg-organic-spices" in home.data

    category_results = client.get("/category/coorg-organic-spices")
    assert b"Black Pepper" in category_results.data
    assert b"Arabica Coffee" not in category_results.data
    assert b"/category/coffee-powder" in home.data
    coffee_results = client.get("/category/coffee-powder")
    assert b"Arabica Coffee" in coffee_results.data
    assert b"Black Pepper" not in coffee_results.data

    search_results = client.get("/shop?q=Organic+Spices")
    assert b"Black Pepper" in search_results.data
    assert b"Arabica Coffee" not in search_results.data


def test_navigation_category_without_products_does_not_404(client):
    response = client.get("/category/coorg-organic-spices")

    assert response.status_code == 200
    assert b"Coorg Organic Spices" in response.data
    assert b"More from this collection is on the way." in response.data
