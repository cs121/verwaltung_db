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
        anmerkungen TEXT,
        stillgelegt INTEGER DEFAULT 0
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
                                item.objekttyp,
                                item.hersteller,
                                item.modell,
                                item.seriennummer,
                                item.einkaufsdatum,
                                item.zuweisungsdatum,
                                item.aktueller_besitzer,
                                item.anmerkungen,
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
                                item.objekttyp,
                                item.hersteller,
                                item.modell,
                                item.seriennummer,
                                item.einkaufsdatum,
                                item.zuweisungsdatum,
                                item.aktueller_besitzer,
                                item.anmerkungen,
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
                conn = self._ensure_conn()
                cursor = conn.execute(
                        "UPDATE items SET aktueller_besitzer = '' WHERE aktueller_besitzer = ?",
                        (owner,),
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
