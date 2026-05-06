"""Pre-load all .pyd files via ctypes so Defender scans them before Python imports them."""
import sys
import os
import ctypes
import pathlib

venv_site = pathlib.Path(r".\.venv\Lib\site-packages")
pyds = list(venv_site.rglob("*.pyd"))
print(f"Pre-loading {len(pyds)} .pyd files...", flush=True)
for pyd in pyds:
    try:
        ctypes.WinDLL(str(pyd.resolve()))
        print(f"  OK: {pyd.name}", flush=True)
    except Exception as e:
        print(f"  ERR {pyd.name}: {e}", flush=True)
print("All pyd files pre-loaded. Now importing sqlalchemy...", flush=True)
import sqlalchemy
print("sqlalchemy imported OK!", flush=True)
sys.exit(0)
