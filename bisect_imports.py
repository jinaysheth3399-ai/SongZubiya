import sys
print("a: sqlite3", flush=True); import sqlite3
print("b: sqlalchemy", flush=True); import sqlalchemy
print("c: dotenv", flush=True); from dotenv import load_dotenv
print("d: pydantic_settings", flush=True); from pydantic_settings import BaseSettings
print("e: backend.config", flush=True); from backend.config import settings
print("f: backend.database (engine create)", flush=True); from backend.database import engine, init_db
print("g: dialect/connect test", flush=True)
with engine.connect() as conn:
    print("   connected ok", flush=True)
print("h: init_db()", flush=True); init_db()
print("done", flush=True)
sys.exit(0)
