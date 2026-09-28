import os

from flask_migrate import upgrade

from app import create_app
from config import Config, ProductionConfig


if os.getenv("FLASK_ENV") == "production":
    ProductionConfig.validate()
    app = create_app(ProductionConfig)
else:
    app = create_app(Config)

# Render starts the app through Gunicorn, so it does not run Flask CLI
# migration commands automatically. Apply pending migrations before the
# server accepts requests (and before templates query categories).
with app.app_context():
    upgrade(directory=os.path.join(os.path.dirname(__file__), "migrations"))


if __name__ == "__main__":
    app.run()
