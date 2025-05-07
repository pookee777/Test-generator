import os
import sys
import logging
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from sqlalchemy.orm import DeclarativeBase
import secrets
from datetime import timedelta

# Add the project root directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if not hasattr(sys, 'real_prefix'):
    sys.real_prefix = getattr(sys, 'base_prefix', sys.prefix)

from extensions import db, login_manager, mail

class Base(DeclarativeBase):
    pass

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static')  # Ensure 'static' is specified
    
    # Update secret key configuration
    app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", secrets.token_hex(32))
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_PERMANENT'] = False
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
    app.config['DEBUG'] = True
    app.config['TIMEZONE'] = 'Asia/Kolkata'
    logger.debug(f"Secret key set to: {app.config['SECRET_KEY']}")

    # Configure SQLite
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'app.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    logger.debug(f"Database URI set to: {app.config['SQLALCHEMY_DATABASE_URI']}")

    # Configure Flask-Mail
    app.config["MAIL_SERVER"] = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    app.config["MAIL_PORT"] = int(os.environ.get("MAIL_PORT", 587))
    app.config["MAIL_USE_TLS"] = os.environ.get("MAIL_USE_TLS", "True").lower() in ["true", "1", "t"]
    app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME", "")
    app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD", "")
    app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("MAIL_DEFAULT_SENDER", "noreply@example.com")
    logger.debug("Mail configuration set")

    # Add a context processor to inject `current_user` into templates
    from flask_login import current_user
    @app.context_processor
    def inject_user():
        return dict(current_user=current_user)

    # Initialize extensions with the app
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'  # Specify the login view
    mail.init_app(app)
    logger.debug("Extensions initialized")

    with app.app_context():
        try:
            from routes import create_routes
            from auth import auth_bp
            
            routes_bp = create_routes()
            app.register_blueprint(routes_bp)  # Register routes blueprint without url_prefix
            app.register_blueprint(auth_bp, url_prefix='/auth')  # Register auth with prefix
            logger.debug("Routes initialized")
        except Exception as e:
            logger.error(f"Failed to initialize routes: {str(e)}")
            raise

        # Create database tables
        db.create_all()
        logger.debug("Database tables created")

    @app.route('/health')
    def health_check():
        try:
            db.session.execute('SELECT 1')
            return "App is running and database is connected!"
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return "Error: Application is having issues", 500

    logger.debug("Flask app created successfully")
    return app


if __name__ == "__main__":
    try:
        app = create_app()
        logger.info("Server starting at http://127.0.0.1:5000")
        app.run(debug=True, host='127.0.0.1', port=5000)
    except Exception as e:
        logger.critical(f"Failed to start application: {e}", exc_info=True)
        sys.exit(1)
