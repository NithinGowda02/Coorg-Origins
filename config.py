import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY") or "local-development-only-change-me"
    database_url = os.getenv("DATABASE_URL")
    if database_url and database_url.startswith(("postgres://", "postgresql://")):
        database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    SQLALCHEMY_DATABASE_URI = database_url or f"sqlite:///{BASE_DIR / 'coorg_flavour.db'}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    UPLOAD_FOLDER = BASE_DIR / "app" / "static" / "uploads" / "products"
    CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
    CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
    CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")
    PAYMENT_QR_PATH = BASE_DIR / "app" / "static" / "uploads" / "payment" / "payment-qr.png"
    UPI_ID = os.getenv("UPI_ID", "replace-with-your-upi-id")
    BRAND_NAME = os.getenv("BRAND_NAME", "Coorg Origins")
    MAIL_SERVER = os.getenv("MAIL_SERVER")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE
    MAX_FORM_MEMORY_SIZE = 2 * 1024 * 1024


class ProductionConfig(Config):
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True

    @classmethod
    def validate(cls):
        if cls.SECRET_KEY == "local-development-only-change-me":
            raise RuntimeError("Set a strong SECRET_KEY before starting production.")
        if cls.UPI_ID == "replace-with-your-upi-id":
            raise RuntimeError("Set UPI_ID before enabling production payments.")
        if not all((cls.CLOUDINARY_CLOUD_NAME, cls.CLOUDINARY_API_KEY, cls.CLOUDINARY_API_SECRET)):
            raise RuntimeError("Set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET before starting production.")
