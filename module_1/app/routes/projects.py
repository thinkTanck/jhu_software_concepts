"""
app/routes/projects.py - Projects Page Blueprint

This module defines the route for the projects page, which displays:
- Project titles
- Project descriptions
- Links to GitHub repositories
"""

from flask import Blueprint, render_template

# Create blueprint for projects page routes
projects_bp = Blueprint('projects', __name__)


@projects_bp.route('/projects')
def projects():
    """
    Render the projects page.

    Returns:
        str: Rendered HTML template for the projects page
    """
    # List of projects to display
    projects_list = [
        {
            'title': 'Module 1: Personal Website',
            'description': """A personal portfolio website built using Flask, a lightweight
            Python web framework. This project demonstrates proficiency in web development
            fundamentals including HTML, CSS, and Python. The website features a responsive
            dark theme design, Flask Blueprints for modular routing, Jinja2 templating for
            dynamic content rendering, and a clean navigation system. The project showcases
            best practices in code organization and follows the MVC architectural pattern.""",
            'github_url': 'https://github.com/thinkTank/jhu_software_concepts',
            'technologies': ['Python', 'Flask', 'HTML5', 'CSS3', 'Jinja2']
        }
    ]

    return render_template('projects.html', projects=projects_list, active_page='projects')
