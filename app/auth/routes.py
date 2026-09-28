from urllib.parse import urljoin, urlparse

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from ..extensions import db
from ..models import User
from .forms import LoginForm
from .signup_form import AdminSignupForm


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def _is_safe_redirect_url(target):
    host_url = urlparse(request.host_url)
    redirect_url = urlparse(urljoin(request.host_url, target))
    return redirect_url.scheme in {"http", "https"} and host_url.netloc == redirect_url.netloc


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user and user.is_active and user.role == "admin" and user.check_password(form.password.data):
            login_user(user)
            next_url = request.args.get("next")
            if next_url and _is_safe_redirect_url(next_url):
                return redirect(next_url)
            return redirect(url_for("admin.dashboard"))
        flash("The email or password is incorrect.", "error")

    setup_available = not User.query.filter_by(role="admin").first()
    return render_template("auth/login.html", form=form, setup_available=setup_available)


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if User.query.filter_by(role="admin").first():
        flash("An administrator account already exists. Please sign in.", "error")
        return redirect(url_for("auth.login"))
    form = AdminSignupForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        if User.query.filter_by(email=email).first():
            form.email.errors.append("That email is already registered.")
        else:
            admin = User(name=form.name.data.strip(), email=email, role="admin")
            admin.set_password(form.password.data)
            db.session.add(admin)
            db.session.commit()
            flash("Admin account created. You can now sign in.", "success")
            return redirect(url_for("auth.login"))
    return render_template("auth/signup.html", form=form)


@auth_bp.post("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been signed out.", "success")
    return redirect(url_for("auth.login"))
