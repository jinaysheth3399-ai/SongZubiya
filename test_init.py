import sys
print("step 1: importing", flush=True)
from backend.database import init_db
print("step 2: calling init_db", flush=True)
init_db()
print("step 3: done", flush=True)
sys.exit(0)
