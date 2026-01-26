================================================================================
                    EN.605.256 - Modern Software Concepts in Python
                    Module 1 Programming Assignment: Personal Website
================================================================================

AUTHOR: Dameion R. Ayers
DATE: 2024

================================================================================
PROJECT DESCRIPTION
================================================================================

This is a personal portfolio website built using Flask, a lightweight Python
web framework. The website features:

- Home page with biography and profile image
- Contact page with email and LinkedIn information
- Projects page showcasing completed work
- Dark theme with responsive navigation
- Clean, professional styling

================================================================================
ENVIRONMENT SETUP
================================================================================

Prerequisites:
- Python 3.10 or newer
- pip (Python package manager)

Setup Steps:

1. Navigate to the module_1 directory:

   cd jhu_software_concepts/module_1

2. (Recommended) Create a virtual environment:

   python -m venv venv

   Activate on Windows:
   venv\Scripts\activate

   Activate on macOS/Linux:
   source venv/bin/activate

3. Install required dependencies:

   pip install -r requirements.txt

================================================================================
RUNNING THE WEBSITE
================================================================================

1. Ensure you are in the module_1 directory:

   cd jhu_software_concepts/module_1

2. Run the application:

   python run.py

3. Open your web browser and navigate to:

   http://localhost:8080

================================================================================
PORT INFORMATION
================================================================================

The application runs on:

- Host: 0.0.0.0 (accessible from localhost and network)
- Port: 8080

Access URLs:
- Home:     http://localhost:8080/
- Contact:  http://localhost:8080/contact
- Projects: http://localhost:8080/projects

================================================================================
PROJECT STRUCTURE
================================================================================

module_1/
├── run.py              # Application entry point
├── requirements.txt    # Python dependencies
├── README.txt          # This file
├── screenshots.pdf     # Screenshots of running website
└── app/
    ├── __init__.py     # Flask app factory
    ├── routes/         # Flask Blueprints for each page
    │   ├── __init__.py
    │   ├── home.py     # Home page route
    │   ├── contact.py  # Contact page route
    │   └── projects.py # Projects page route
    ├── templates/      # Jinja2 HTML templates
    │   ├── base.html   # Shared base template
    │   ├── home.html   # Home page template
    │   ├── contact.html# Contact page template
    │   └── projects.html# Projects page template
    └── static/         # Static assets
        ├── css/
        │   └── style.css   # Main stylesheet (dark theme)
        └── images/
            └── profile.jpg # Profile image

================================================================================
TECHNOLOGIES USED
================================================================================

- Python 3.10+
- Flask 2.3+
- Jinja2 (templating)
- HTML5
- CSS3

================================================================================
FEATURES
================================================================================

1. Navigation Bar:
   - Appears on every page
   - Positioned in top-right corner
   - Highlights active page with distinct color
   - Smooth hover effects

2. Dark Theme:
   - Dark background colors
   - Light text for readability
   - Accent colors for visual interest

3. Responsive Design:
   - Adapts to different screen sizes
   - Mobile-friendly layout

4. Flask Blueprints:
   - Modular routing architecture
   - Separate modules for each page

================================================================================
TROUBLESHOOTING
================================================================================

Issue: Port 8080 already in use
Solution: Stop any other application using port 8080, or modify run.py
          to use a different port.

Issue: Module not found errors
Solution: Ensure you've installed dependencies with pip install -r requirements.txt

Issue: Profile image not displaying
Solution: Ensure profile.jpg exists in app/static/images/

================================================================================
