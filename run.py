import os

from app import create_app
from config import Config, ProductionConfig


if os.getenv("FLASK_ENV") == "production":
    ProductionConfig.validate()
    app = create_app(ProductionConfig)
else:
    app = create_app(Config)


if __name__ == "__main__":
    app.run()
