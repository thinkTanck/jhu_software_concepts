"""
app/routes/home.py - Home Page Blueprint

This module defines the route for the home page, which displays:
- Name and position
- Biography (left side)
- Profile image (right side)
"""

from flask import Blueprint, render_template

# Create blueprint for home page routes
home_bp = Blueprint('home', __name__)


@home_bp.route('/')
def home():
    """
    Render the home page.

    Returns:
        str: Rendered HTML template for the home page
    """
    # Personal information to display on home page
    personal_info = {
        'name': 'Dameion R. Ayers',
        'position': 'PM, Construction Engineer & Graduate Student',
        'biography': (
            "I am the founder of Ayers and Associates, a façade engineering firm serving the "
            "commercial glass and glazing industry. My path to engineering and artificial "
            "intelligence has been unconventional. I spent fifteen years incarcerated in the "
            "federal prison system, where I redirected my life through education, discipline, "
            "and long-term focus.\n\n"
            "During that time, I completed a four-year architectural drafting apprenticeship, "
            "earned an associate's degree in business administration (summa cum laude), began "
            "my bachelor's degree in mathematics, and taught adult continuing education courses "
            "in algebra and business writing. I completed my mathematics degree shortly after "
            "release, graduating summa cum laude.\n\n"
            "After returning to the workforce, I advanced through roles in design, engineering "
            "management, and project executive leadership on complex façade projects across the "
            "United States and internationally. I am currently pursuing a master's degree in "
            "Artificial Intelligence at Johns Hopkins University, where my focus is on rigorous "
            "systems thinking, modeling, and the responsible application of AI in real-world "
            "engineering and educational contexts."
        ),
        'profile_image': 'images/profile.jpg'
    }

    return render_template('home.html', info=personal_info, active_page='home')
