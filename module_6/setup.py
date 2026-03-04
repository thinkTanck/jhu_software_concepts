"""
setup.py — Module 6 packaging configuration.

Install the package and its runtime dependencies with:

    pip install -e .

Or for a regular (non-editable) install:

    pip install .
"""
from setuptools import setup

setup(
    name="module_6_gradcafe",
    version="1.0.0",
    description="GradCafe Admissions Analysis — Module 6: Deploy Anywhere",
    packages=[],
    install_requires=[
        "Flask>=3.0",
        "psycopg[binary]>=3.1",
        "pika>=1.3",
    ],
    python_requires=">=3.11",
)
