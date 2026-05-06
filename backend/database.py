from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session

from backend.config import settings


# SQLite needs check_same_thread=False to be used across FastAPI threads
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args, future=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

Base = declarative_base()


def get_db() -> Session:
    """FastAPI dependency that yields a SQLAlchemy session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Import models, create tables, and apply lightweight column migrations."""
    from backend import models  # noqa: F401  (registers models on Base)
    from sqlalchemy import text

    Base.metadata.create_all(bind=engine)

    # Lightweight in-place migrations for SQLite.
    # If the playlists table predates the (drive_root_name, name) composite unique
    # constraint, recreate it. This drops the old `name UNIQUE` so two playlists in
    # different Drive roots can share the same folder name.
    with engine.begin() as conn:
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(playlists)"))}
        needs_rebuild = "drive_root_name" not in cols
        if not needs_rebuild:
            # Also rebuild if the legacy single-column unique index still exists.
            indexes = list(conn.execute(text("PRAGMA index_list(playlists)")))
            for _, idx_name, unique, *_ in indexes:
                if not unique:
                    continue
                cols_in_idx = [
                    r[2] for r in conn.execute(text(f"PRAGMA index_info({idx_name})"))
                ]
                if cols_in_idx == ["name"]:
                    needs_rebuild = True
                    break

        if needs_rebuild:
            from backend.config import settings

            conn.execute(text("""
                CREATE TABLE playlists_new (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    drive_folder_id TEXT,
                    drive_root_name TEXT,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    UNIQUE (drive_root_name, name)
                )
            """))
            # Copy existing rows; drive_root_name is set to the env-configured root
            # so old playlists keep pointing at the same Drive folder hierarchy.
            has_root_col = "drive_root_name" in cols
            if has_root_col:
                conn.execute(text("""
                    INSERT INTO playlists_new
                        (id, name, drive_folder_id, drive_root_name, created_at, updated_at)
                    SELECT id, name, drive_folder_id, drive_root_name, created_at, updated_at
                      FROM playlists
                """))
            else:
                conn.execute(text("""
                    INSERT INTO playlists_new
                        (id, name, drive_folder_id, drive_root_name, created_at, updated_at)
                    SELECT id, name, drive_folder_id, NULL, created_at, updated_at
                      FROM playlists
                """))
            conn.execute(
                text("UPDATE playlists_new SET drive_root_name = :root "
                     "WHERE drive_root_name IS NULL OR drive_root_name = ''"),
                {"root": settings.GOOGLE_DRIVE_ROOT_FOLDER_NAME},
            )
            conn.execute(text("DROP TABLE playlists"))
            conn.execute(text("ALTER TABLE playlists_new RENAME TO playlists"))
