"""
run.py - Entry point for the Flask Personal Website application.

This module initializes and runs the Flask application on port 8080.
Usage: python run.py
"""

from app import create_app

# Create the Flask application instance
app = create_app()

if __name__ == "__main__":
    # Run the application on port 8080 as required
    # Debug mode enabled for development
    app.run(host="0.0.0.0", port=8080, debug=True)
