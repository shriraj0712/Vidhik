"""
Vidhik Platform - Database Connection & Session Management
==========================================================
Manages thread-safe PostgreSQL connection pooling for FastAPI endpoints.
All database operations are read-only and consume environment variables.
"""

import os
from pathlib import Path
from contextlib import contextmanager
from typing import Generator
import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load environment variables from backend/.env if available
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "vidhik_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

DB_MIN_CONN = int(os.getenv("DB_MIN_CONN", "1"))
DB_MAX_CONN = int(os.getenv("DB_MAX_CONN", "10"))

# Global connection pool reference
_pool: ThreadedConnectionPool = None


def init_db_pool():
    """Initializes the PostgreSQL connection pool."""
    global _pool
    if _pool is None or _pool.closed:
        _pool = ThreadedConnectionPool(
            minconn=DB_MIN_CONN,
            maxconn=DB_MAX_CONN,
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )


def close_db_pool():
    """Closes all database connections in the pool."""
    global _pool
    if _pool and not _pool.closed:
        _pool.closeall()
        _pool = None


def get_db_connection():
    """Retrieves a connection from the pool."""
    global _pool
    if _pool is None or _pool.closed:
        init_db_pool()
    return _pool.getconn()


def release_db_connection(conn):
    """Releases a connection back to the pool."""
    global _pool
    if _pool and not _pool.closed and conn:
        _pool.putconn(conn)


@contextmanager
def get_db_cursor() -> Generator[RealDictCursor, None, None]:
    """
    Context manager that yields a dictionary-based cursor (RealDictCursor).
    Automatically returns the connection to the pool upon exit.
    """
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            yield cur
    finally:
        release_db_connection(conn)


def get_db() -> Generator[RealDictCursor, None, None]:
    """
    FastAPI dependency that yields a database cursor for request handlers.
    """
    with get_db_cursor() as cur:
        yield cur


def check_db_connection() -> dict:
    """
    Pings the PostgreSQL database and returns connection health diagnostics.
    """
    try:
        with get_db_cursor() as cur:
            cur.execute("SELECT 1 AS ping, current_database() AS db_name, version() AS version;")
            row = cur.fetchone()
            return {
                "status": "connected",
                "database": row["db_name"],
                "version": row["version"].split(",")[0]
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
