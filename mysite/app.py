from flask import Flask

from .config import DefaultConfig
from .models import db
from .routes import admin


def create_app(config) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config)
    app.secret_key = config.KEY
    app.register_blueprint(admin)
    app.config['SQLALCHEMY_DATABASE_URI'] = config.DATA_BASE
    db.init_app(app)
    return app


def run_app() -> any:
    app = create_app(DefaultConfig)
    # create_database_structure(app)
    return app.run()
