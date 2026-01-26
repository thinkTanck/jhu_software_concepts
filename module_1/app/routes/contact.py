"""
app/routes/contact.py - Contact Page Blueprint

This module defines the route for the contact page, which displays:
- Email address
- LinkedIn information
"""

from flask import Blueprint, render_template

# Create blueprint for contact page routes
contact_bp = Blueprint('contact', __name__)


@contact_bp.route('/contact')
def contact():
    """
    Render the contact page.

    Returns:
        str: Rendered HTML template for the contact page
    """
    # Contact information to display
    contact_info = {
        'email': 'dayers6@jh.edu',
        'linkedin_url': 'https://www.linkedin.com/in/dameion-a-662aa880',
        'linkedin_text': 'https://www.linkedin.com/in/dameion-a-662aa880'
    }

    return render_template('contact.html', contact=contact_info, active_page='contact')
