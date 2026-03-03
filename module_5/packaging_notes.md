# Why Packaging Matters — Module 5

`setup.py` and `requirements.txt` are not mere formalities; they make the project
reliably installable, testable, and distributable across machines and CI environments.

1. **Installability** — `pip install -e .` installs the `src` package in editable mode
   so `import src.app`, `from src import load_data`, etc., resolve correctly from any
   working directory without manually manipulating `sys.path` or `PYTHONPATH`.

2. **Import / path correctness** — `packages=["src"]` in `setup.py` tells setuptools
   exactly which top-level package to register.  Without this, running `pytest` from the
   repo root would fail with `ModuleNotFoundError: No module named 'src'` unless the caller
   happened to be in the right directory.

3. **Reproducibility** — `requirements.txt` pins minimum-version constraints for every
   dependency.  Any developer (or CI runner) who runs `pip install -r requirements.txt`
   gets a compatible, predictable environment regardless of what is already installed
   globally.

4. **CI integration** — GitHub Actions installs the project cleanly in two commands:
   ```
   pip install -r requirements.txt
   pip install -e .
   ```
   No `PYTHONPATH=module_5` hacks, no `conftest.py` path tricks, no `sys.path.insert`
   in test files.  The package is just importable, the same way it is in production.

5. **Separation of concerns** — `install_requires` in `setup.py` declares *runtime*
   dependencies (Flask, psycopg, python-dotenv).  `requirements.txt` adds *development*
   dependencies (pytest, pylint, Sphinx, pydeps).  Keeping them separate mirrors the
   distinction between what users of the package need and what developers need.

6. **Versioning** — `version="1.0.0"` provides a single source of truth.  Tools like
   `pip`, `pip-compile`, and Dependabot can reference this version for pinned installs
   (`pip install module_5_gradcafe==1.0.0`) and changelog / audit trails.

7. **Dependency auditing** — Security scanners (Snyk, Safety, Dependabot) read
   `requirements.txt` to detect known CVEs in the dependency tree.  Without a
   `requirements.txt`, automated vulnerability scanning cannot determine which packages
   are in use — the Snyk scan in Step 6 depends directly on this file.

8. **Distribution readiness** — Running `pip install build && python -m build` would
   produce a distributable wheel (`.whl`) and source distribution (`.tar.gz`) that could
   be uploaded to a private registry or PyPI, enabling the project to be shared and
   consumed as a proper Python package.
