from flask import Flask


def create_app():
    app = Flask(__name__)

    from app.routes.books import books_bp
    from app.routes.members import members_bp
    from app.routes.loans import loans_bp
    from app.routes.reservations import reservations_bp
    from app.routes.views import views_bp

    app.register_blueprint(books_bp)
    app.register_blueprint(members_bp)
    app.register_blueprint(loans_bp)
    app.register_blueprint(reservations_bp)
    app.register_blueprint(views_bp)

    return app
