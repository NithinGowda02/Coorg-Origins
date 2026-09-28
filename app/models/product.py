from datetime import datetime, timezone

from ..extensions import db


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False, index=True)
    name = db.Column(db.String(180), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False, index=True)
    short_description = db.Column(db.String(500), nullable=True)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    is_featured = db.Column(db.Boolean, nullable=False, default=False, index=True)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    category = db.relationship("Category", back_populates="products")
    images = db.relationship(
        "ProductImage", back_populates="product", cascade="all, delete-orphan", order_by="ProductImage.display_order"
    )
    variants = db.relationship(
        "ProductVariant", back_populates="product", cascade="all, delete-orphan"
    )


class ProductImage(db.Model):
    __tablename__ = "product_images"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    image_url = db.Column(db.String(500), nullable=False)
    alt_text = db.Column(db.String(255), nullable=False)
    display_order = db.Column(db.Integer, nullable=False, default=0)
    is_primary = db.Column(db.Boolean, nullable=False, default=False)

    product = db.relationship("Product", back_populates="images")


class ProductVariant(db.Model):
    __tablename__ = "product_variants"
    __table_args__ = (
        db.UniqueConstraint("product_id", "label", name="uq_product_variant_label"),
    )

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    sku = db.Column(db.String(80), unique=True, nullable=False, index=True)
    label = db.Column(db.String(80), nullable=False)
    quantity_value = db.Column(db.Numeric(10, 3), nullable=False)
    quantity_unit = db.Column(db.String(20), nullable=False)
    price = db.Column(db.Numeric(12, 2), nullable=False)
    stock_quantity = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    product = db.relationship("Product", back_populates="variants")
    cart_items = db.relationship("CartItem", back_populates="variant")
    order_items = db.relationship("OrderItem", back_populates="variant")
