"""Project-wide Python startup tweaks.

Python imports this module automatically when the project root is on sys.path.
Keeping this tiny lets ad-hoc scripts such as ``python test_sa.py`` avoid
loading SQLAlchemy's optional compiled extensions on Windows.
"""

from __future__ import annotations

import os


os.environ.setdefault("DISABLE_SQLALCHEMY_CEXT_RUNTIME", "1")
