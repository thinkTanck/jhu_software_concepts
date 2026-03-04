Overview & Setup
================

This module extends the GradCafe data pipeline from Modules 2 and 3 by adding
a comprehensive test suite, 100% code coverage, GitHub Actions CI, and Sphinx
documentation.

About the Application
---------------------

The application scrapes graduate admissions data from GradCafe, stores it in a
PostgreSQL database, and exposes a web interface for querying and visualizing
the results.

Environment Variables
---------------------

.. envvar:: DATABASE_URL

   A `libpq`-compatible PostgreSQL connection string, for example::

       postgresql://postgres:password@localhost:5432/gradcafe_module3

   This is the **only** required environment variable.  If not set, the app
   falls back to the local development default.

How to Run the Application
--------------------------

1. Install dependencies::

       pip install -r module_4/requirements.txt

2. Set the ``DATABASE_URL`` environment variable::

       export DATABASE_URL=postgresql://postgres:password@localhost:5432/gradcafe_module3

3. Run the Flask development server from the repo root::

       python module_4/src/app.py

4. Open a browser to ``http://127.0.0.1:5000/analysis``.

How to Run the Tests
--------------------

From the **repository root** (not from inside ``module_4/``)::

    pytest -m "web or buttons or analysis or db or integration" module_4/tests/

This runs the complete marked test suite with coverage enforcement (100%).

To run with the full ``pytest.ini`` settings (coverage + fail-under)::

    pytest --co -q   # dry-run to see collected tests
    pytest           # full run

Read the Docs
-------------

Online documentation is published at:

https://gradcafe-module4.readthedocs.io  *(placeholder — replace with your actual RTD URL)*
