import re
from io import BytesIO
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename

from ..extensions import db
from ..models import CartItem, Category, Order, OrderItem, Product, ProductImage, ProductVariant
from ..notifications import send_order_status_email
from .decorators import admin_required
from .product_forms import ProductForm
from .order_forms import OrderStatusForm
from .payment_qr_form import PaymentQrForm


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.get("/")
@login_required
@admin_required
def dashboard():
    metrics = {
        "products": Product.query.count(),
        "orders": Order.query.count(),
        "low_stock": ProductVariant.query.filter(
            ProductVariant.is_active.is_(True), ProductVariant.stock_quantity <= 5
        ).count(),
        "pending_payments": Order.query.filter_by(payment_status="pending_verification").count(),
    }
    return render_template("admin/dashboard.html", metrics=metrics)


@admin_bp.route("/payment-qr", methods=["GET", "POST"])
@login_required
@admin_required
def payment_qr_settings():
    form = PaymentQrForm()
    qr_path = Path(current_app.config["PAYMENT_QR_PATH"])
    if form.validate_on_submit():
        try:
            form.image.data.stream.seek(0)
            with Image.open(form.image.data.stream) as image:
                if image.width < 64 or image.height < 64:
                    raise ValueError("The QR image must be at least 64 by 64 pixels.")
                if image.width * image.height > 10_000_000:
                    raise ValueError("The QR image must be smaller than 10 megapixels.")
                image.load()
                if image.mode in {"RGBA", "LA"} or "transparency" in image.info:
                    rgba = image.convert("RGBA")
                    normalized = Image.new("RGB", rgba.size, "white")
                    normalized.paste(rgba, mask=rgba.getchannel("A"))
                else:
                    normalized = image.convert("RGB")
                qr_path.parent.mkdir(parents=True, exist_ok=True)
                normalized.save(qr_path, format="PNG", optimize=True)
        except (UnidentifiedImageError, OSError, ValueError) as error:
            form.image.errors.append(str(error) or "Choose a valid image file.")
        else:
            flash("Payment QR image updated.", "success")
            return redirect(url_for("admin.payment_qr_settings"))
    return render_template(
        "admin/payment_qr.html",
        form=form,
        qr_image_url=(
            f"{url_for('static', filename='uploads/payment/payment-qr.png')}?v={qr_path.stat().st_mtime_ns}"
            if qr_path.is_file()
            else None
        ),
    )


def _slugify(value):
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _default_category():
    category = Category.query.filter_by(slug="other").first()
    if not category:
        category = Category(name="Other", slug="other", description="Other Coorg products")
        db.session.add(category)
        db.session.flush()
    category.is_active = True
    return category


def _validate_variants(form, product_id=None):
    labels = set()
    is_valid = True
    for entry in form.variants.entries:
        variant_form = entry.form
        label = variant_form.label.data.strip().lower() if variant_form.label.data else ""
        variant_id = int(variant_form.id.data) if variant_form.id.data else None
        if label in labels:
            variant_form.label.errors.append("Variant labels must be unique within this product.")
            is_valid = False
        labels.add(label)
    return is_valid


def _generated_sku(product, label, variant_id=None):
    base = f"{product.slug}-{_slugify(label)}".upper().replace("-", "-")[:70]
    candidate = base
    suffix = 2
    while True:
        with db.session.no_autoflush:
            existing = ProductVariant.query.filter_by(sku=candidate).first()
        if not existing or existing.id == variant_id:
            return candidate
        candidate = f"{base[:75-len(str(suffix))-1]}-{suffix}"
        suffix += 1


def _save_variants(product, form):
    existing = {variant.id: variant for variant in product.variants}
    for entry in form.variants.entries:
        variant_form = entry.form
        variant_id = int(variant_form.id.data) if variant_form.id.data else None
        variant = existing.get(variant_id) if variant_id else ProductVariant(product=product)
        if variant is None:
            continue
        variant.label = variant_form.label.data.strip()
        variant.quantity_value = variant_form.quantity_value.data
        variant.quantity_unit = variant_form.quantity_unit.data.strip()
        variant.price = variant_form.price.data
        variant.stock_quantity = variant_form.stock_quantity.data
        if not variant_id or not variant.sku:
            variant.sku = _generated_sku(product, variant.label, variant_id)
        variant.is_active = variant_form.is_active.data
        if variant_id is None:
            db.session.add(variant)


def _save_product_images(product, files, *, prepend=False):
    cloudinary_values = (
        current_app.config.get("CLOUDINARY_CLOUD_NAME"),
        current_app.config.get("CLOUDINARY_API_KEY"),
        current_app.config.get("CLOUDINARY_API_SECRET"),
    )
    use_cloudinary = all(cloudinary_values)
    if any(cloudinary_values) and not use_cloudinary:
        raise ImageStorageError("Cloudinary credentials are incomplete.")

    upload_folder = Path(current_app.config["UPLOAD_FOLDER"])
    if not use_cloudinary:
        upload_folder.mkdir(parents=True, exist_ok=True)
    valid_images = []
    for image_file in files or []:
        if not image_file or not image_file.filename:
            continue
        safe_name = secure_filename(image_file.filename)
        extension = Path(safe_name).suffix.lower()
        if extension not in {".jpg", ".jpeg", ".png", ".webp"}:
            continue
        try:
            image_file.stream.seek(0)
            with Image.open(image_file.stream) as image:
                image.verify()
            image_file.stream.seek(0)
        except (UnidentifiedImageError, OSError):
            continue
        valid_images.append((image_file, safe_name, extension))

    if prepend and valid_images:
        for existing_image in product.images:
            existing_image.display_order += len(valid_images)
            existing_image.is_primary = False

    next_order = 0 if prepend else len(product.images)
    for image_file, safe_name, extension in valid_images:
        filename = f"{uuid4().hex}{extension}"
        if use_cloudinary:
            import cloudinary
            from cloudinary import uploader

            cloudinary.config(
                cloud_name=cloudinary_values[0],
                api_key=cloudinary_values[1],
                api_secret=cloudinary_values[2],
                secure=True,
            )
            payload = BytesIO(image_file.stream.read())
            payload.name = safe_name
            try:
                upload_result = uploader.upload(
                    payload,
                    folder="coorg-origins/products",
                    resource_type="image",
                    allowed_formats=["jpg", "jpeg", "png", "webp"],
                )
            except Exception as error:
                current_app.logger.exception("Cloudinary product image upload failed.")
                raise ImageStorageError("Image storage is temporarily unavailable. Please try again.") from error
            image_url = upload_result.get("secure_url")
            if not image_url:
                raise ImageStorageError("Image storage did not return a secure image URL.")
        else:
            image_file.save(upload_folder / filename)
            image_url = f"/static/uploads/products/{filename}"
        db.session.add(
            ProductImage(
                product=product,
                image_url=image_url,
                alt_text=product.name,
                display_order=next_order,
                is_primary=next_order == 0 and (prepend or not product.images),
            )
        )
        next_order += 1


class ImageStorageError(Exception):
    pass


def _populate_product_form(form, product):
    form.name.data = product.name
    form.category_id.data = product.category_id
    form.short_description.data = product.short_description
    form.description.data = product.description
    form.is_active.data = product.is_active
    form.is_featured.data = product.is_featured
    for index, variant in enumerate(product.variants):
        if index == len(form.variants.entries):
            form.variants.append_entry()
        variant_form = form.variants.entries[index].form
        variant_form.id.data = variant.id
        variant_form.label.data = variant.label
        variant_form.quantity_value.data = variant.quantity_value
        variant_form.quantity_unit.data = variant.quantity_unit
        variant_form.price.data = variant.price
        variant_form.stock_quantity.data = variant.stock_quantity
        variant_form.sku.data = variant.sku
        variant_form.is_active.data = variant.is_active


@admin_bp.get("/products")
@login_required
@admin_required
def products():
    product_list = Product.query.order_by(Product.created_at.desc()).all()
    return render_template("admin/products.html", products=product_list)


def _configure_product_categories(form, selected_category_id=None):
    standard_categories = [
        ("Coorg Organic Spices", "coorg-organic-spices", ("coorg-organic-spices", "organic-spices", "coorg-spices", "spices")),
        ("Coorg Masala Powders", "coorg-masala-powders", ("coorg-masala-powders", "masala-powders", "masala")),
        ("Coorg Coffee", "coorg-coffee", ("coorg-coffee", "coffee", "coffee-powder")),
        ("Sour & Tangy Fruits", "sour-tangy-fruits", ("sour-tangy-fruits", "sour-and-tangy-fruits")),
    ]
    added_standard_category = False
    all_categories = Category.query.all()
    known_slugs = {category.slug.lower() for category in all_categories}
    known_names = {category.name.strip().lower() for category in all_categories}
    for name, slug, aliases in standard_categories:
        category_exists = any(alias in known_slugs for alias in aliases) or any(
            alias.replace("-", " ") in known_names for alias in aliases
        )
        if not category_exists:
            db.session.add(Category(name=name, slug=slug, description=f"{name} from Coorg", is_active=True))
            added_standard_category = True
    if added_standard_category:
        db.session.commit()

    categories = Category.query.filter_by(is_active=True).order_by(Category.name.asc()).all()
    if not categories:
        categories = [_default_category()]
        db.session.commit()
    if selected_category_id:
        selected = db.session.get(Category, selected_category_id)
        if selected and all(category.id != selected.id for category in categories):
            categories.append(selected)
            categories.sort(key=lambda category: category.name.lower())
    form.category_id.choices = [(category.id, category.name) for category in categories]
    if categories and form.category_id.data is None:
        if selected_category_id and any(category.id == selected_category_id for category in categories):
            form.category_id.data = selected_category_id
        elif request.method == "GET" or "category_id" not in request.form:
            form.category_id.data = categories[0].id


@admin_bp.route("/products/new", methods=["GET", "POST"])
@login_required
@admin_required
def new_product():
    form = ProductForm()
    _configure_product_categories(form)
    if form.validate_on_submit():
        slug = _slugify(form.name.data)
        duplicate_slug = Product.query.filter_by(slug=slug).first()
        if not slug:
            form.name.errors.append("Enter a product name containing letters or numbers.")
        elif duplicate_slug:
            form.name.errors.append("A product with that name already exists.")
        elif _validate_variants(form):
            product = Product(
                name=form.name.data.strip(),
                slug=slug,
                category_id=form.category_id.data,
                short_description=form.short_description.data.strip() if form.short_description.data else None,
                description=form.description.data.strip() if form.description.data else None,
                is_active=True,
                is_featured=form.is_featured.data,
            )
            db.session.add(product)
            db.session.flush()
            _save_variants(product, form)
            try:
                _save_product_images(product, form.images.data)
            except ImageStorageError as error:
                db.session.rollback()
                form.images.errors.append(str(error))
                flash("Product was not saved because image storage failed.", "error")
                return render_template("admin/product_form.html", form=form, product=None)
            db.session.commit()
            flash("Product created.", "success")
            return redirect(url_for("admin.products"))
    return render_template("admin/product_form.html", form=form, product=None)


@admin_bp.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_product(product_id):
    product = db.get_or_404(Product, product_id)
    form = ProductForm()
    _configure_product_categories(form, product.category_id)
    if request.method == "GET":
        _populate_product_form(form, product)
    if form.validate_on_submit():
        slug = _slugify(form.name.data)
        duplicate_slug = Product.query.filter(Product.slug == slug, Product.id != product.id).first()
        if not slug:
            form.name.errors.append("Enter a product name containing letters or numbers.")
        elif duplicate_slug:
            form.name.errors.append("Another product with that name already exists.")
        elif _validate_variants(form, product.id):
            product.name = form.name.data.strip()
            product.slug = slug
            product.category_id = form.category_id.data
            product.short_description = form.short_description.data.strip() if form.short_description.data else None
            product.description = form.description.data.strip() if form.description.data else None
            product.is_active = form.is_active.data
            product.is_featured = form.is_featured.data
            _save_variants(product, form)
            try:
                _save_product_images(product, form.images.data, prepend=True)
            except ImageStorageError as error:
                db.session.rollback()
                form.images.errors.append(str(error))
                flash("Product changes were not saved because image storage failed.", "error")
                product = db.get_or_404(Product, product_id)
                return render_template("admin/product_form.html", form=form, product=product)
            db.session.commit()
            flash("Product updated.", "success")
            return redirect(url_for("admin.products"))
    return render_template("admin/product_form.html", form=form, product=product)


@admin_bp.post("/products/<int:product_id>/delete")
@login_required
@admin_required
def delete_product(product_id):
    product = db.get_or_404(Product, product_id)
    variant_ids = db.select(ProductVariant.id).where(ProductVariant.product_id == product.id)
    CartItem.query.filter(CartItem.variant_id.in_(variant_ids)).delete(synchronize_session=False)
    OrderItem.query.filter(OrderItem.variant_id.in_(variant_ids)).update(
        {OrderItem.variant_id: None}, synchronize_session=False
    )
    db.session.delete(product)
    db.session.commit()
    flash("Product deleted. Previous order history has been preserved.", "success")
    return redirect(url_for("admin.products"))


@admin_bp.get("/orders")
@login_required
@admin_required
def orders():
    order_list = Order.query.order_by(Order.created_at.desc()).limit(100).all()
    return render_template("admin/orders.html", orders=order_list)


@admin_bp.route("/orders/<int:order_id>", methods=["GET", "POST"])
@login_required
@admin_required
def order_detail(order_id):
    order = db.get_or_404(Order, order_id)
    form = OrderStatusForm()
    if request.method == "GET":
        form.order_status.data = order.order_status
    if form.validate_on_submit():
        previous_status = order.order_status
        order.order_status = form.order_status.data
        db.session.commit()
        if order.order_status != previous_status:
            has_payment_reference = any(payment.transaction_reference for payment in order.payments)
            if not has_payment_reference:
                flash("Order status updated. The customer email will be sent after a payment reference is submitted.", "success")
            elif send_order_status_email(order):
                flash("Order status updated and customer notified.", "success")
            else:
                flash("Order status updated, but the customer email could not be sent. Check SMTP settings and server logs.", "error")
        else:
            flash("Order status is unchanged.", "success")
        return redirect(url_for("admin.order_detail", order_id=order.id))
    return render_template("admin/order_detail.html", order=order, form=form)


@admin_bp.post("/orders/<int:order_id>/delete")
@login_required
@admin_required
def delete_order(order_id):
    order = db.get_or_404(Order, order_id)
    db.session.delete(order)
    db.session.commit()
    flash("Order and its payment records were deleted.", "success")
    return redirect(url_for("admin.orders"))


@admin_bp.post("/orders/<int:order_id>/verify-payment")
@login_required
@admin_required
def verify_payment(order_id):
    order = db.get_or_404(Order, order_id)
    payment = order.payments[-1] if order.payments else None
    if payment and payment.transaction_reference:
        previous_status = order.order_status
        payment.payment_status = "verified"
        payment.verified_by = current_user.id
        payment.verified_at = datetime.now(timezone.utc)
        order.payment_status = "verified"
        if order.order_status == "pending":
            order.order_status = "confirmed"
        db.session.commit()
        if order.order_status != previous_status:
            send_order_status_email(order)
        flash("Payment verified and order confirmed.", "success")
    else:
        flash("A transaction reference is required before verification.", "error")
    return redirect(url_for("admin.order_detail", order_id=order.id))
