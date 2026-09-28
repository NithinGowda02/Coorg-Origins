import click
from flask import Flask, jsonify, render_template
from flask.cli import with_appcontext

from config import Config
from .extensions import csrf, db, login_manager, migrate
from .auth import auth_bp
from .admin import admin_bp
from .cart import cart_bp
from .checkout import checkout_bp
from .main import main_bp
from .models import Category, User


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    csrf.init_app(app)

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(cart_bp)
    app.register_blueprint(checkout_bp)

    @app.errorhandler(404)
    def not_found(error):
        if request_accepts_json():
            return jsonify(error="not_found"), 404
        return render_template("errors/404.html"), 404

    @app.errorhandler(413)
    def request_too_large(error):
        return render_template("errors/413.html"), 413

    @app.errorhandler(500)
    def server_error(error):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @app.cli.command("create-admin")
    @with_appcontext
    def create_admin():
        """Create an administrator without storing credentials in source code."""
        email = click.prompt("Admin email").strip().lower()
        if User.query.filter_by(email=email).first():
            raise click.ClickException("A user with that email already exists.")
        name = click.prompt("Admin name")
        password = click.prompt("Admin password", hide_input=True, confirmation_prompt=True)
        admin = User(name=name, email=email, role="admin")
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        click.echo(f"Created admin account for {email}.")

    @app.context_processor
    def inject_brand_name():
        active_categories = Category.query.filter_by(is_active=True).all()
        category_by_slug = {category.slug.lower(): category for category in active_categories}
        category_by_name = {category.name.strip().lower(): category for category in active_categories}
        nav_category_specs = [
            ("Coorg Organic Spices", "coorg-organic-spices", ("coorg-organic-spices", "organic-spices", "coorg-spices", "spices")),
            ("Coorg Masala Powders", "coorg-masala-powders", ("coorg-masala-powders", "masala-powders", "masala")),
            ("Coorg Coffee", "coorg-coffee", ("coorg-coffee", "coffee", "coffee-powder")),
            ("Sour & Tangy Fruits", "sour-tangy-fruits", ("sour-tangy-fruits", "sour-and-tangy-fruits")),
        ]
        nav_categories = []
        for label, fallback_slug, aliases in nav_category_specs:
            category = next((category_by_slug[alias] for alias in aliases if alias in category_by_slug), None)
            if category is None:
                category = next((category_by_name[alias.replace("-", " ")] for alias in aliases if alias.replace("-", " ") in category_by_name), None)
            nav_categories.append({"name": label, "slug": category.slug if category else fallback_slug})
        return {
            "brand_name": app.config["BRAND_NAME"],
            "nav_categories": nav_categories,
        }

    return app


def request_accepts_json():
    from flask import request

    return request.accept_mimetypes.best == "application/json"
