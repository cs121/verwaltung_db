from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List, Optional

from .models import Item
from .repository import AbstractRepository, RepositoryError

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        objekttyp TEXT,
        hersteller TEXT,
        modell TEXT,
        seriennummer TEXT,
        einkaufsdatum TEXT,
        zuweisungsdatum TEXT,
        aktueller_besitzer TEXT,
        anmerkungen TEXT
);
"""


class SQLiteRepository(AbstractRepository):
        """SQLite-Implementation der Repository-Schnittstelle."""

        def __init__(self, db_path: Path) -> None:
                super().__init__()
                self.db_path = Path(db_path)
                self.connection: Optional[sqlite3.Connection] = None

        def initialize(self) -> None:
                self.connection = sqlite3.connect(self.db_path)
                self.connection.row_factory = sqlite3.Row
                self.connection.execute("PRAGMA foreign_keys = ON")
                self.connection.execute(SCHEMA)
                self._migrate_schema()
                self.connection.execute(SCHEMA)
                self.connection.commit()

        def _migrate_schema(self) -> None:
                conn = self._ensure_conn()
                cursor = conn.execute("PRAGMA table_info(items)")
                columns = [row[1] for row in cursor.fetchall()]
                expected = [
                        'id',
                        'objekttyp',
                        'hersteller',
                        'modell',
                        'seriennummer',
                        'einkaufsdatum',
                        'zuweisungsdatum',
                        'aktueller_besitzer',
                        'anmerkungen',
                ]
                if not columns or columns == expected:
                        return
                conn.execute(
                        """
                        CREATE TABLE IF NOT EXISTS items_migrated (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                objekttyp TEXT,
                                hersteller TEXT,
                                modell TEXT,
                                seriennummer TEXT,
                                einkaufsdatum TEXT,
                                zuweisungsdatum TEXT,
                                aktueller_besitzer TEXT,
                                anmerkungen TEXT
                        )
                        """
                )
                has_assignment = 'zuweisungsdatum' in columns
                copy_query = """
                INSERT INTO items_migrated (
                        id, objekttyp, hersteller, modell, seriennummer,
                        einkaufsdatum, zuweisungsdatum, aktueller_besitzer, anmerkungen
                )
                SELECT
                        id,
                        COALESCE(objekttyp, ''),
                        COALESCE(hersteller, ''),
                        COALESCE(modell, ''),
                        COALESCE(seriennummer, ''),
                        COALESCE(einkaufsdatum, ''),
                        {zuweisungsdatum},
                        COALESCE(aktueller_besitzer, ''),
                        COALESCE(anmerkungen, '')
                FROM items
                """.format(
                        zuweisungsdatum="COALESCE(zuweisungsdatum, '')" if has_assignment else "''"
                )
                conn.execute(copy_query)
                conn.execute("DROP TABLE items")
                conn.execute("ALTER TABLE items_migrated RENAME TO items")
                conn.commit()

        def _ensure_conn(self) -> sqlite3.Connection:
                if not self.connection:
                        raise RepositoryError("SQLite Verbindung nicht initialisiert")
                return self.connection

        def list(self, filters: Optional[dict] = None) -> List[Item]:
                conn = self._ensure_conn()
                query = "SELECT * FROM items"
                params: list = []
                allowed_keys = {
                        'objekttyp',
                        'hersteller',
                        'modell',
                        'seriennummer',
                        'einkaufsdatum',
                        'zuweisungsdatum',
                        'aktueller_besitzer',
                        'anmerkungen',
                }
                if filters:
                        conditions = []
                        for key, value in filters.items():
                                if value is None or value == "":
                                        continue
                                if key not in allowed_keys:
                                        continue
                                conditions.append(f"{key} LIKE ?")
                                params.append(f"%{value}%")
                        if conditions:
                                query += " WHERE " + " AND ".join(conditions)
                query += " ORDER BY objekttyp COLLATE NOCASE, modell COLLATE NOCASE"
                rows = conn.execute(query, params).fetchall()
                return [Item.from_row(row) for row in rows]

        def get(self, item_id: int) -> Optional[Item]:
                conn = self._ensure_conn()
                row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
                return Item.from_row(row) if row else None

        def create(self, item: Item) -> Item:
                conn = self._ensure_conn()
                cursor = conn.execute(
                        """
                        INSERT INTO items (
                                objekttyp, hersteller, modell, seriennummer,
                                einkaufsdatum, zuweisungsdatum, aktueller_besitzer, anmerkungen
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                                item.objekttyp,
                                item.hersteller,
                                item.modell,
                                item.seriennummer,
                                item.einkaufsdatum,
                                item.zuweisungsdatum,
                                item.aktueller_besitzer,
                                item.anmerkungen,
                        ),
                )
                conn.commit()
                return item.copy(id=cursor.lastrowid)

        def update(self, item_id: int, item: Item) -> Item:
                conn = self._ensure_conn()
                conn.execute(
                        """
                        UPDATE items SET
                                objekttyp=?, hersteller=?, modell=?, seriennummer=?,
                                einkaufsdatum=?, zuweisungsdatum=?, aktueller_besitzer=?, anmerkungen=?
                        WHERE id = ?
                        """,
                        (
                                item.objekttyp,
                                item.hersteller,
                                item.modell,
                                item.seriennummer,
                                item.einkaufsdatum,
                                item.zuweisungsdatum,
                                item.aktueller_besitzer,
                                item.anmerkungen,
                                item_id,
                        ),
                )
                conn.commit()
                return item.copy(id=item_id)

        def delete(self, item_id: int) -> None:
                conn = self._ensure_conn()
                conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
                conn.commit()

        def distinct_owners(self) -> List[str]:
                conn = self._ensure_conn()
                rows = conn.execute(
                        "SELECT DISTINCT aktueller_besitzer FROM items WHERE aktueller_besitzer <> '' ORDER BY aktueller_besitzer COLLATE NOCASE"
                ).fetchall()
                return [row[0] for row in rows if row[0]]

        def distinct_object_types(self) -> List[str]:
                conn = self._ensure_conn()
                rows = conn.execute(
                        "SELECT DISTINCT objekttyp FROM items WHERE objekttyp <> '' ORDER BY objekttyp COLLATE NOCASE"
                ).fetchall()
                return [row[0] for row in rows if row[0]]

        def distinct_manufacturers(self) -> List[str]:
                conn = self._ensure_conn()
                rows = conn.execute(
                        "SELECT DISTINCT hersteller FROM items WHERE hersteller <> '' ORDER BY hersteller COLLATE NOCASE"
                ).fetchall()
                return [row[0] for row in rows if row[0]]

        def distinct_models(self) -> List[str]:
                conn = self._ensure_conn()
                rows = conn.execute(
                        "SELECT DISTINCT modell FROM items WHERE modell <> '' ORDER BY modell COLLATE NOCASE"
                ).fetchall()
                return [row[0] for row in rows if row[0]]
