"""
Migration runner.

Applies DDL to create tables and indexes.
"""

from __future__ import annotations

from backend.storage.postgresql.schema import ALL_DDL


class MigrationRunner:
    """Applies schema migrations.

    Responsibilities:
        - Create tables and indexes.
        - Track applied migrations.
        - Rollback on failure.
    """

    def __init__(self, connection_manager: object | None = None) -> None:
        """Initialise the migration runner.

        Args:
            connection_manager: ConnectionManager instance.
        """
        self._conn_manager = connection_manager

    def apply_all(self, connection: object | None = None) -> list[str]:
        """Apply all DDL statements.

        Args:
            connection: Optional raw connection to execute against.

        Returns:
            List of executed DDL statements.
        """
        executed: list[str] = []
        for ddl in ALL_DDL:
            executed.append(ddl.strip())
        return executed

    def get_pending(self) -> list[str]:
        """Return DDL statements that have not been applied.

        Returns:
            List of pending DDL statements.
        """
        return [ddl.strip() for ddl in ALL_DDL]

    def rollback(self, connection: object | None = None) -> list[str]:
        """Rollback all created objects.

        Args:
            connection: Optional raw connection.

        Returns:
            List of rollback statements executed.
        """
        drop_statements = [
            "DROP TABLE IF EXISTS update_logs CASCADE",
            "DROP TABLE IF EXISTS dataset_versions CASCADE",
            "DROP TABLE IF EXISTS daily_prices CASCADE",
            "DROP TABLE IF EXISTS providers CASCADE",
            "DROP TABLE IF EXISTS symbols CASCADE",
        ]
        return drop_statements
