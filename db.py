"""
SonoBot — Database Layer
MySQL connection pooling and low-level query helpers.
"""

import logging
from contextlib import contextmanager

import mysql.connector
from mysql.connector import pooling

from config import (
    DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_PORT, DB_POOL_SIZE,
)

logger = logging.getLogger("sonobot.db")

# ---------------------------------------------------------------------------
# Connection Pool
# ---------------------------------------------------------------------------

_pool = None


def _get_pool():
    """Lazily creates and returns the shared connection pool."""
    global _pool
    if _pool is None:
        logger.info(
            "Creating MySQL connection pool (size=%d, db=%s, host=%s:%d)",
            DB_POOL_SIZE, DB_NAME, DB_HOST, DB_PORT,
        )
        _pool = pooling.MySQLConnectionPool(
            pool_name="sonobot_pool",
            pool_size=DB_POOL_SIZE,
            pool_reset_session=True,
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            port=DB_PORT,
        )
    return _pool


@contextmanager
def get_db_connection():
    """Context manager that borrows a connection from the pool.

    Usage::

        with get_db_connection() as (connection, cursor):
            cursor.execute("SELECT ...")
            rows = cursor.fetchall()
    """
    connection = None
    cursor = None
    try:
        connection = _get_pool().get_connection()
        cursor = connection.cursor(dictionary=True)
        yield connection, cursor
    except mysql.connector.Error as err:
        logger.error("Database error: %s", err)
        raise
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def db_execute(query, params=None, fetch="all"):
    """Convenience helper: run a query and return results.

    Args:
        query: SQL query string with %s placeholders.
        params: Tuple/list of parameters.
        fetch: "all" | "one" | "none".
    """
    with get_db_connection() as (connection, cursor):
        cursor.execute(query, params or [])
        if fetch == "all":
            return cursor.fetchall()
        elif fetch == "one":
            return cursor.fetchone()
        return None
