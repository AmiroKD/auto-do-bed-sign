from .auth import auth_bp
# from .users import users_bp  # TODO: 待实现 (Task 7)
# from .logs import logs_bp  # TODO: 待实现 (Task 8)


def register_blueprints(app):
    app.register_blueprint(auth_bp)
    # app.register_blueprint(users_bp)  # TODO: 待实现 (Task 7)
    # app.register_blueprint(logs_bp)  # TODO: 待实现 (Task 8)
