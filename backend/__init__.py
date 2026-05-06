"""Backend package startup hooks."""

from __future__ import annotations

import os


# SQLAlchemy's Cython extensions are optional. On some Windows setups Defender
# can stall while scanning the .pyd files, so prefer the pure-Python fallback.
os.environ.setdefault("DISABLE_SQLALCHEMY_CEXT_RUNTIME", "1")
