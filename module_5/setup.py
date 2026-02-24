"""
setup.py — Module 5 packaging configuration.

Install the src package and its runtime dependencies with:

    pip install -e .

Or for a regular (non-editable) install:

    pip install .
"""
from setuptools import setup

setup(
    name="module_5_gradcafe",
    version="1.0.0",
    description="GradCafe Admissions Analysis — Module 5: Secure SQL & SQLi Defense",
    packages=["src"],
    install_requires=[
        "Flask>=3.0",
        "psycopg[binary]>=3.1",
        "python-dotenv>=1.0",
    ],
    python_requires=">=3.11",
)
