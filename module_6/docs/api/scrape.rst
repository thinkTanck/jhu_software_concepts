Scraper (scrape.py)
====================

The scraper is located in ``module_2/scrape.py`` (outside the ``src/`` package).
It is invoked dynamically by ``_default_scraper()`` in ``app.py``.

.. note::

   The scraper is not part of the ``module_4/src`` package and is therefore
   not shown via autodoc here.  Its responsibility is to fetch raw GradCafe
   admissions submissions and return them as a list of dicts.

Expected output format::

    [
        {
            "notes": "MIT | Computer Science | Fall 2026 | ...",
            "program": "Computer Science",
            "decision": "Accepted",
            "gpa": "3.9",
            "decision_date": "January 15, 2026",
            "llm-generated-program": "Computer Science",
            "llm-generated-university": "MIT",
        },
        ...
    ]
