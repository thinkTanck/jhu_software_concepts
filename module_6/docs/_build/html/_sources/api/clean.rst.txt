Data Cleaner (clean.py)
========================

The cleaner is located in ``module_2/clean.py`` (outside the ``src/`` package).
It is used by the module_2 pipeline to normalize raw scraped data before it is
passed to the loader.

.. note::

   ``clean.py`` is not part of the ``module_4/src`` package and is not shown
   via autodoc here.  Its responsibility is to normalize scraped rows:

   - Trim whitespace from string fields
   - Standardize status values (Accepted, Rejected, Waitlisted)
   - Normalize GPA and GRE values to numeric types

The cleaned output is consumed by ``load_data.load_rows()``.
