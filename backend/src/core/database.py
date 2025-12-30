import psycopg2
from psycopg2 import pool
from typing import Optional, Any
from src.core.config import DB_URL, MAX_WORKERS

class DatabaseManager:
    _instance: Optional['DatabaseManager'] = None
    _pool: Optional[psycopg2.pool.ThreadedConnectionPool] = None

    def __new__(cls) -> 'DatabaseManager':
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance

    def initialize_pool(self) -> None:
        if self._pool is None:
            if not DB_URL:
                raise ValueError("DB_URL environment variable is not set")
            # Allow up to two database connections per worker (to support concurrent
            # operations such as separate read/write or background tasks) plus a small
            # fixed overhead for non-worker usage (e.g., health checks, admin queries).
            # This keeps the pool large enough for peak thread usage without exhausting
            # the database with unbounded connections.
            pool_size = (MAX_WORKERS * 2) + 2
            self._pool = psycopg2.pool.ThreadedConnectionPool(1, pool_size, DB_URL)

    def get_connection(self) -> Any:
        """
        Retrieves a connection from the pool.
        """
        if self._pool is None:
            self.initialize_pool()
        
        # FIX FOR MYPY: Explicitly check if pool is still None after initialization
        if self._pool is None:
            raise RuntimeError("Database pool failed to initialize correctly.")

        return self._pool.getconn()

    def release_connection(self, conn: Any) -> None:
        """
        Returns a connection to the pool.
        """
        if self._pool and conn:
            self._pool.putconn(conn)

    def close_pool(self) -> None:
        """
        Closes all connections in the pool.
        """
        if self._pool:
            self._pool.closeall()
            self._pool = None