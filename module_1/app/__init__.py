"""
app/__init__.py - Flask Application Factory

This module creates and configures the Flask application instance.
It registers all blueprints for routing and sets up the application context.
"""

from flask import Flask


def create_app():
    """
    Application factory function that creates and configures the Flask app.

    Returns:
        Flask: Configured Flask application instance
    """
    # Create Flask application instance
    app = Flask(__name__)

    # Configure the application
    app.config['SECRET_KEY'] = 'dev-secret-key-for-module-1'

    # Import and register blueprints for each page
    from app.routes.home import home_bp
    from app.routes.contact import contact_bp
    from app.routes.projects import projects_bp

    # Register blueprints with the application
    app.register_blueprint(home_bp)
    app.register_blueprint(contact_bp)
    app.register_blueprint(projects_bp)

    return app
