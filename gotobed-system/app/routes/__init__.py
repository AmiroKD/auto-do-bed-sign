from .auth import auth_bp
from .users import users_bp
from .logs import logs_bp


def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(logs_bp)
