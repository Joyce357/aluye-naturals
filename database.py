"""
Database abstraction layer for Aluyè Naturals.

Provides SQLAlchemy Core engine management and high-level query helpers
while maintaining 100% backward compatibility with existing SQLite usage
and test configurations (ADMIN_DATABASE, local SQLite files, tempfile DBs).
"""

import os
from contextlib import contextmanager
from pathlib import Path
from flask import current_app, g
from sqlalchemy import create_engine, text

_engines = {}


def _get_data_dir(app=None):
    """
    Locate data directory for persistent disk (DATA_DIR) or local instance folder.
    Self-contained helper to avoid circular dependencies with admin.py.
    """
    data_dir = os.environ.get("DATA_DIR")
    if data_dir:
        path = Path(data_dir)
    elif app and hasattr(app, "instance_path"):
        path = Path(app.instance_path)
    else:
        path = Path("instance")
    path.mkdir(parents=True, exist_ok=True)
    return path


def _normalize_db_url(url):
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def _sqlite_url_from_path(path):
    p = Path(path).as_posix()
    return f"sqlite:///{p}"


def build_db_url(app=None):
    """
    Determine the database connection URL based on strict priority order:
    1. app.config["DATABASE_URL"]
    2. app.config["ADMIN_DATABASE"]
    3. os.environ["DATABASE_URL"]
    4. os.environ["ADMIN_DATABASE"]
    5. default local SQLite instance path
    """
    if app and app.config.get("DATABASE_URL"):
        return _normalize_db_url(app.config["DATABASE_URL"])

    if app and app.config.get("ADMIN_DATABASE"):
        return _sqlite_url_from_path(app.config["ADMIN_DATABASE"])

    if os.environ.get("DATABASE_URL"):
        return _normalize_db_url(os.environ["DATABASE_URL"])

    if os.environ.get("ADMIN_DATABASE"):
        return _sqlite_url_from_path(os.environ["ADMIN_DATABASE"])

    db_path = str(_get_data_dir(app) / "aluye_admin.db")
    return _sqlite_url_from_path(db_path)




def get_engine(app=None):
    """
    Retrieve or create the SQLAlchemy engine for the application context.
    Engines are cached by unique URL to support multi-app test isolation.
    """
    target_app = app
    if not target_app and current_app:
        try:
            target_app = current_app._get_current_object()
        except Exception:
            target_app = None

    if target_app and "_db_engine" in target_app.config:
        return target_app.config["_db_engine"]

    url = build_db_url(target_app)

    if url in _engines:
        engine = _engines[url]
        if target_app:
            target_app.config["_db_engine"] = engine
        return engine

    engine_kwargs = {}

    if url.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}

    engine = create_engine(url, **engine_kwargs)

    if target_app:
        target_app.config["_db_engine"] = engine
    _engines[url] = engine

    return engine


def get_db():
    """
    Get the legacy database connection for the current request context.

    NOTE: This returns a raw SQLite DBAPI connection specifically for existing legacy code
    that relies on raw SQLite APIs (?, executescript(), sqlite3.Row).

    DATABASE_URL may create a SQLAlchemy engine, but legacy get_db() remains SQLite-only
    until future query migration phases convert calls to SQLAlchemy Core helpers
    (fetch_one, fetch_all, execute_write).
    """
    if "admin_db" not in g:
        app = current_app._get_current_object()
        engine = get_engine(app)

        if engine.dialect.name != "sqlite":
            raise RuntimeError(
                f"Legacy get_db() is restricted to SQLite (current dialect: '{engine.dialect.name}'). "
                "Non-SQLite databases require migrating query calls to database.py SQLAlchemy Core helpers "
                "(fetch_one, fetch_all, execute_write)."
            )

        raw_conn = engine.raw_connection()
        dbapi_conn = getattr(raw_conn, "dbapi_connection", getattr(raw_conn, "driver_connection", raw_conn))
        if hasattr(dbapi_conn, "row_factory"):
            import sqlite3
            dbapi_conn.row_factory = sqlite3.Row

        g.admin_db = raw_conn

    return g.admin_db


def close_db(_error=None):
    """
    Close the database connection associated with the current request context.
    """
    db = g.pop("admin_db", None)
    if db is not None:
        try:
            db.close()
        except Exception:
            pass


def init_app(app):
    """
    Initialize database extension with the Flask app.
    Registers teardown_appcontext to ensure clean connection teardown.
    """
    app.teardown_appcontext(close_db)
    get_engine(app)


# High-level SQLAlchemy Core Abstraction API
def fetch_one(sql, params=None):
    """
    Execute query and fetch a single row as a dictionary while connection is active.
    Prevents live SQLAlchemy Result objects from escaping closed connection context.
    """
    engine = get_engine()
    stmt = text(sql) if isinstance(sql, str) else sql
    with engine.connect() as conn:
        result = conn.execute(stmt, params or {})
        row = result.mappings().first()
        return dict(row) if row is not None else None


def fetch_all(sql, params=None):
    """
    Execute query and fetch all rows as a list of dictionaries while connection is active.
    Prevents live SQLAlchemy Result objects from escaping closed connection context.
    """
    engine = get_engine()
    stmt = text(sql) if isinstance(sql, str) else sql
    with engine.connect() as conn:
        result = conn.execute(stmt, params or {})
        return [dict(row) for row in result.mappings().all()]


def execute_write(sql, params=None):
    """
    Execute a write statement (INSERT/UPDATE/DELETE) with auto-commit while connection is active.
    Returns dictionary with execution metadata (e.g., rowcount).
    """
    engine = get_engine()
    stmt = text(sql) if isinstance(sql, str) else sql
    with engine.begin() as conn:
        result = conn.execute(stmt, params or {})
        return {"rowcount": result.rowcount}


def execute_query(sql, params=None):
    """
    Execute a read query and return all materialized mapping dictionaries.
    Convenience alias for fetch_all.
    """
    return fetch_all(sql, params)


@contextmanager
def transaction():
    """Context manager for explicit transaction boundaries via SQLAlchemy Core."""
    engine = get_engine()
    with engine.begin() as conn:
        yield conn
