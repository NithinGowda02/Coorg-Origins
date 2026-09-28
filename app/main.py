from flask import Blueprint, Response, abort, jsonify, render_template, request, url_for
from sqlalchemy.orm import joinedload, selectinload

from .extensions import db
from .models import Category, Product, ProductVariant


main_bp = Blueprint("main", __name__)


@main_bp.get("/")
def home():
    product_options = (
        Product.query.join(ProductVariant)
        .filter(
            Product.is_active.is_(True),
            ProductVariant.is_active.is_(True),
            ProductVariant.stock_quantity > 0,
        )
        .options(selectinload(Product.variants), selectinload(Product.images), joinedload(Product.category))
        .distinct()
        .order_by(Product.created_at.desc())
    )
    featured_products = product_options.all()
    return render_template(
        "home.html",
        featured_products=featured_products,
    )


@main_bp.get("/shop")
def shop():
    return _render_shop()


@main_bp.get("/category/<slug>")
def category_page(slug):
    category = Category.query.filter_by(slug=slug, is_active=True).first()
    if category:
        return _render_shop(category_slug=category.slug, category_name=category.name, category_endpoint=True)

    reserved_categories = {
        "coorg-organic-spices": "Coorg Organic Spices",
        "coorg-masala-powders": "Coorg Masala Powders",
        "coorg-coffee": "Coorg Coffee",
        "sour-tangy-fruits": "Sour & Tangy Fruits",
    }
    category_name = reserved_categories.get(slug)
    if category_name is None:
        abort(404)
    return _render_shop(category_slug=slug, category_name=category_name, category_endpoint=True)


def _render_shop(category_slug=None, category_name=None, category_endpoint=False):
    search = request.args.get("q", "").strip()
    if category_slug is None:
        category_slug = request.args.get("category", "").strip()
    sort = request.args.get("sort", "newest")
    page = max(request.args.get("page", 1, type=int), 1)

    query = (
        Product.query.join(ProductVariant)
        .filter(
            Product.is_active.is_(True),
            ProductVariant.is_active.is_(True),
            ProductVariant.stock_quantity > 0,
        )
        .options(selectinload(Product.variants), selectinload(Product.images), joinedload(Product.category))
        .distinct()
    )


    if search:
        search_term = f"%{search}%"
        query = query.filter(
            db.or_(
                Product.name.ilike(search_term),
                Product.short_description.ilike(search_term),
                Product.description.ilike(search_term),
                Product.category.has(Category.name.ilike(search_term)),
            )
        )
    if category_slug:
        query = query.join(Category).filter(Category.slug == category_slug, Category.is_active.is_(True))

    lowest_price = (
        db.select(db.func.min(ProductVariant.price))
        .where(
            ProductVariant.product_id == Product.id,
            ProductVariant.is_active.is_(True),
            ProductVariant.stock_quantity > 0,
        )
        .correlate(Product)
        .scalar_subquery()
    )
    if sort == "name":
        query = query.order_by(Product.name.asc())
    elif sort == "price_low":
        query = query.order_by(lowest_price.asc())
    elif sort == "price_high":
        query = query.order_by(lowest_price.desc())
    else:
        query = query.order_by(Product.created_at.desc())

    products = query.paginate(page=page, per_page=12, error_out=False)
    categories = Category.query.filter_by(is_active=True).order_by(Category.name.asc()).all()
    if category_name is None and category_slug:
        category_name = next((category.name for category in categories if category.slug == category_slug), None)
    return render_template(
        "shop.html",
        products=products,
        categories=categories,
        search=search,
        category_slug=category_slug,
        category_name=category_name,
        category_endpoint=category_endpoint,
        sort=sort,
    )


@main_bp.get("/our-story")
def our_story():
    featured_product = (
        Product.query.join(ProductVariant)
        .filter(
            Product.is_active.is_(True),
            ProductVariant.is_active.is_(True),
            ProductVariant.stock_quantity > 0,
        )
        .options(selectinload(Product.images))
        .distinct()
        .order_by(Product.created_at.desc())
        .first()
    )
    categories = Category.query.filter_by(is_active=True).order_by(Category.name.asc()).all()
    return render_template("our_story.html", featured_product=featured_product, categories=categories)


@main_bp.get("/product/<slug>")
def product_detail(slug):
    product = (
        Product.query.options(
            selectinload(Product.variants),
            selectinload(Product.images),
            joinedload(Product.category),
        )
        .filter_by(slug=slug, is_active=True)
        .first_or_404()
    )
    active_variants = [
        variant for variant in product.variants if variant.is_active
    ]
    if not active_variants:
        abort(404)
    related_products = (
        Product.query.join(ProductVariant)
        .filter(
            Product.category_id == product.category_id,
            Product.id != product.id,
            Product.is_active.is_(True),
            ProductVariant.is_active.is_(True),
            ProductVariant.stock_quantity > 0,
        )
        .options(selectinload(Product.images), selectinload(Product.variants), joinedload(Product.category))
        .distinct()
        .limit(4)
        .all()
    )
    return render_template(
        "product_detail.html",
        product=product,
        active_variants=active_variants,
        related_products=related_products,
    )


@main_bp.get("/healthz")
def health_check():
    return jsonify(status="ok")


@main_bp.get("/sitemap.xml")
def sitemap():
    urls = [url_for("main.home", _external=True), url_for("main.shop", _external=True)]
    urls.extend(
        url_for("main.product_detail", slug=product.slug, _external=True)
        for product in Product.query.filter_by(is_active=True).all()
    )
    body = "".join(f"<url><loc>{url}</loc></url>" for url in urls)
    return Response(
        f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{body}</urlset>',
        mimetype="application/xml",
    )


@main_bp.get("/robots.txt")
def robots():
    return Response(
        f"User-agent: *\nAllow: /\nDisallow: /admin/\nDisallow: /auth/\nSitemap: {url_for('main.sitemap', _external=True)}\n",
        mimetype="text/plain",
    )
