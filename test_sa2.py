import sys
print("1: langhelpers", flush=True)
import sqlalchemy.util.langhelpers
print("2: compat", flush=True)
import sqlalchemy.util.compat
print("3: deprecations", flush=True)
import sqlalchemy.util.deprecations
print("4: concurrency", flush=True)
import sqlalchemy.util.concurrency
print("5: done", flush=True)
sys.exit(0)
