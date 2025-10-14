from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List, Optional

from .models import Item
from .repository import AbstractRepository, RepositoryError
from ..utils.constants import DEFAULT_OWNER

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
        anmerkungen TEXT,
        stillgelegt INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS custom_values (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,
        value TEXT NOT NULL,
        UNIQUE(category, value COLLATE NOCASE)
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
                self.connection.executescript(SCHEMA)
                self._migrate_schema()
                self.connection.executescript(SCHEMA)
                self.connection.commit()

        @staticmethod
        def _db_value(value: Optional[str]) -> Optional[str]:
                if value is None:
                        return None
                text = value.strip()
                return text or None

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
                        'stillgelegt',
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
                                anmerkungen TEXT,
                                stillgelegt INTEGER DEFAULT 0
                        )
                        """
                )
                has_assignment = 'zuweisungsdatum' in columns
                has_deactivation = 'stillgelegt' in columns
                copy_query = """
                INSERT INTO items_migrated (
                        id, objekttyp, hersteller, modell, seriennummer,
                        einkaufsdatum, zuweisungsdatum, aktueller_besitzer, anmerkungen, stillgelegt
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
                        COALESCE(anmerkungen, ''),
                        {stillgelegt}
                FROM items
                """.format(
                        zuweisungsdatum="COALESCE(zuweisungsdatum, '')" if has_assignment else "''",
                        stillgelegt="COALESCE(stillgelegt, 0)" if has_deactivation else "0",
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
                conditions: list[str] = []
                allowed_keys = [
                        'objekttyp',
                        'hersteller',
                        'modell',
                        'seriennummer',
                        'einkaufsdatum',
                        'zuweisungsdatum',
                        'aktueller_besitzer',
                        'anmerkungen',
                ]
                global_search = None
                if filters:
                        filters_copy = dict(filters)
                        global_search = filters_copy.pop('__global__', None)
                        for key, value in filters_copy.items():
                                if value is None or value == "":
                                        continue
                                if key not in allowed_keys:
                                        continue
                                conditions.append(f"{key} LIKE ?")
                                params.append(f"%{value}%")
                if global_search:
                        like_value = f"%{global_search}%"
                        like_conditions = [f"{key} LIKE ?" for key in allowed_keys]
                        conditions.append("(" + " OR ".join(like_conditions) + ")")
                        params.extend([like_value] * len(like_conditions))
                if conditions:
                        query += " WHERE " + " AND ".join(conditions)
                query += " ORDER BY objekttyp COLLATE NOCASE, modell COLLATE NOCASE"
                rows = conn.execute(query, params).fetchall()
                items: list[Item] = []
                notes_updated = False
                for row in rows:
                        item = Item.from_row(row)
                        updated_item = item.with_stillgelegt_note()
                        if updated_item.anmerkungen != item.anmerkungen and updated_item.id is not None:
                                conn.execute(
                                        "UPDATE items SET anmerkungen = ? WHERE id = ?",
                                        (updated_item.anmerkungen, updated_item.id),
                                )
                                notes_updated = True
                        items.append(updated_item)
                if notes_updated:
                        conn.commit()
                return items

        def get(self, item_id: int) -> Optional[Item]:
                conn = self._ensure_conn()
                row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
                return Item.from_row(row).with_stillgelegt_note() if row else None

        def create(self, item: Item) -> Item:
                conn = self._ensure_conn()
                item = item.with_stillgelegt_note()
                cursor = conn.execute(
                        """
                        INSERT INTO items (
                                objekttyp, hersteller, modell, seriennummer,
                                einkaufsdatum, zuweisungsdatum, aktueller_besitzer, anmerkungen, stillgelegt
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                                self._db_value(item.objekttyp),
                                self._db_value(item.hersteller),
                                self._db_value(item.modell),
                                self._db_value(item.seriennummer),
                                self._db_value(item.einkaufsdatum),
                                self._db_value(item.zuweisungsdatum),
                                self._db_value(item.aktueller_besitzer),
                                self._db_value(item.anmerkungen),
                                int(item.stillgelegt),
                        ),
                )
                conn.commit()
                return item.copy(id=cursor.lastrowid)

        def update(self, item_id: int, item: Item) -> Item:
                conn = self._ensure_conn()
                item = item.with_stillgelegt_note()
                conn.execute(
                        """
                        UPDATE items SET
                                objekttyp=?, hersteller=?, modell=?, seriennummer=?,
                                einkaufsdatum=?, zuweisungsdatum=?, aktueller_besitzer=?, anmerkungen=?, stillgelegt=?
                        WHERE id = ?
                        """,
                        (
                                self._db_value(item.objekttyp),
                                self._db_value(item.hersteller),
                                self._db_value(item.modell),
                                self._db_value(item.seriennummer),
                                self._db_value(item.einkaufsdatum),
                                self._db_value(item.zuweisungsdatum),
                                self._db_value(item.aktueller_besitzer),
                                self._db_value(item.anmerkungen),
                                int(item.stillgelegt),
                                item_id,
                        ),
                )
                conn.commit()
                return item.copy(id=item_id)

        def delete(self, item_id: int) -> None:
                conn = self._ensure_conn()
                conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
                conn.commit()

        def deactivate(self, item_id: int) -> Item:
                conn = self._ensure_conn()
                item = self.get(item_id)
                if not item:
                        raise RepositoryError('Item nicht gefunden')
                updated = item.copy(stillgelegt=True).with_stillgelegt_note()
                conn.execute(
                        "UPDATE items SET stillgelegt = 1, anmerkungen = ? WHERE id = ?",
                        (updated.anmerkungen, item_id),
                )
                conn.commit()
                return updated

        def distinct_owners(self) -> List[str]:
                conn = self._ensure_conn()
                rows = conn.execute(
                        "SELECT DISTINCT aktueller_besitzer FROM items WHERE aktueller_besitzer <> '' ORDER BY aktueller_besitzer COLLATE NOCASE"
                ).fetchall()
                return [row[0] for row in rows if row[0]]

        def clear_owner(self, owner: str) -> int:
                if owner.strip().lower() == DEFAULT_OWNER.lower():
                        return 0

                conn = self._ensure_conn()
                cursor = conn.execute(
                        "UPDATE items SET aktueller_besitzer = ? WHERE aktueller_besitzer = ?",
                        (DEFAULT_OWNER, owner),
                )
                conn.commit()
                return cursor.rowcount

        def clear_serial_number(self, serial_number: str) -> int:
                conn = self._ensure_conn()
                cursor = conn.execute(
                        "UPDATE items SET seriennummer = '' WHERE seriennummer = ?",
                        (serial_number,),
                )
                conn.commit()
                return cursor.rowcount

        def clear_object_type(self, object_type: str) -> int:
                conn = self._ensure_conn()
                cursor = conn.execute(
                        "UPDATE items SET objekttyp = '' WHERE objekttyp = ?",
                        (object_type,),
                )
                conn.commit()
                return cursor.rowcount

        def clear_manufacturer(self, manufacturer: str) -> int:
                conn = self._ensure_conn()
                cursor = conn.execute(
                        "UPDATE items SET hersteller = '' WHERE hersteller = ?",
                        (manufacturer,),
                )
                conn.commit()
                return cursor.rowcount

        def clear_model(self, model: str) -> int:
                conn = self._ensure_conn()
                cursor = conn.execute(
                        "UPDATE items SET modell = '' WHERE modell = ?",
                        (model,),
                )
                conn.commit()
                return cursor.rowcount

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

        def distinct_serial_numbers(self) -> List[str]:
                conn = self._ensure_conn()
                rows = conn.execute(
                        "SELECT DISTINCT seriennummer FROM items WHERE seriennummer <> '' ORDER BY seriennummer COLLATE NOCASE"
                ).fetchall()
                return [row[0] for row in rows if row[0]]

        def list_custom_values(self, category: str) -> List[str]:
                conn = self._ensure_conn()
                rows = conn.execute(
                        "SELECT value FROM custom_values WHERE category = ? ORDER BY value COLLATE NOCASE",
                        (category,),
                ).fetchall()
                return [row[0] for row in rows if row[0]]

        def add_custom_value(self, category: str, value: str) -> None:
                conn = self._ensure_conn()
                cleaned = value.strip()
                if not cleaned:
                        return
                conn.execute(
                        "INSERT OR IGNORE INTO custom_values (category, value) VALUES (?, ?)",
                        (category, cleaned),
                )
                conn.commit()

        def remove_custom_value(self, category: str, value: str) -> None:
                conn = self._ensure_conn()
                cleaned = value.strip()
                if not cleaned:
                        return
                conn.execute(
                        "DELETE FROM custom_values WHERE category = ? AND value = ?",
                        (category, cleaned),
                )
                conn.commit()
