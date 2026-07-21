"""
Database connection manager.

Handles connection lifecycle, pool management,
transactions, rollback, and graceful shutdown.
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker


@dataclass(frozen=True)
class DatabaseConfig:
    """Immutable database configuration.

    Attributes:
        host:     Database host.
        port:     Database port.
        database: Database name.
        username: Database user.
        password: Database password.
        pool_size: Connection pool size.
        max_overflow: Maximum overflow connections.
        echo:     Log SQL statements.
    """

    host: str = "localhost"
    port: int = 5432
    database: str = "zime"
    username: str = "zime"
    password: str = ""
    pool_size: int = 5
    max_overflow: int = 10
    echo: bool = False

    @property
    def url(self) -> str:
        """Return SQLAlchemy connection URL."""
        if self.password:
            return (
                f"postgresql+psycopg://{self.username}:{self.password}"
                f"@{self.host}:{self.port}/{self.database}"
            )
        return (
            f"postgresql+psycopg://{self.username}"
            f"@{self.host}:{self.port}/{self.database}"
        )


class ConnectionManager:
    """Manages PostgreSQL connection lifecycle.

    Responsibilities:
        - Connection pool management.
        - Transaction context managers.
        - Rollback on failure.
        - Graceful shutdown.
    """

    def __init__(self, config: DatabaseConfig | None = None, engine: Engine | None = None) -> None:
        """Initialise the connection manager.

        Args:
            config: Database configuration (ignored if engine is provided).
            engine: Pre-configured SQLAlchemy engine (for testing).
        """
        if engine is not None:
            self._engine = engine
            self._session_factory = sessionmaker(bind=engine)
        elif config is not None:
            self._engine = create_engine(
                config.url,
                pool_size=config.pool_size,
                max_overflow=config.max_overflow,
                echo=config.echo,
            )
            self._session_factory = sessionmaker(bind=self._engine)
        else:
            raise ValueError("Either config or engine must be provided")

    @property
    def engine(self) -> Engine:
        """Return the underlying SQLAlchemy engine."""
        return self._engine

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Provide a transactional session scope.

        Yields:
            SQLAlchemy Session.

        Raises:
            Exception: Rolls back on any exception.
        """
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @contextmanager
    def transaction(self) -> Generator[Session, None, None]:
        """Provide an atomic transaction scope.

        Yields:
            SQLAlchemy Session.

        Raises:
            Exception: Rolls back on any exception.
        """
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def dispose(self) -> None:
        """Dispose of all connections in the pool."""
        self._engine.dispose()

    def is_connected(self) -> bool:
        """Check if the database is reachable.

        Returns:
            True if connection succeeds.
        """
        try:
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False
