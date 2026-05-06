import os, sys
print(f"DISABLE_SQLALCHEMY_CEXT_RUNTIME={os.environ.get('DISABLE_SQLALCHEMY_CEXT_RUNTIME', 'NOT SET')}", flush=True)
print("importing sqlalchemy.util._has_cy...", flush=True)
from sqlalchemy.util._has_cy import HAS_CYEXTENSION
print(f"HAS_CYEXTENSION={HAS_CYEXTENSION}", flush=True)
print("done", flush=True)
sys.exit(0)
