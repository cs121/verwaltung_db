
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List, Optional

from .constants import DEFAULT_OBJECT_TYPES
from .models import Item
from .repository import AbstractRepository, RepositoryError

SCHEMA_ITEMS = """
CREATE TABLE IF NOT EXISTS items (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	objekttyp TEXT,
	hersteller TEXT,
	modell TEXT,
	seriennummer TEXT,
	einkaufsdatum TEXT,
	aktueller_besitzer TEXT,
	anmerkungen TEXT,
	zuweisungsdatum TEXT
);
"""

SCHEMA_OBJECT_TYPES = """
CREATE TABLE IF NOT EXISTS object_types (
	name TEXT PRIMARY KEY COLLATE NOCASE
);
"""

INSERT_ITEM = """
INSERT INTO items (
	objekttyp, hersteller, modell, seriennummer, einkaufsdatum,
	aktueller_besitzer, anmerkungen, zuweisungsdatum
) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
"""

UPDATE_ITEM = """
UPDATE items SET
	objekttyp=?, hersteller=?, modell=?, seriennummer=?,
	einkaufsdatum=?, aktueller_besitzer=?, anmerkungen=?, zuweisungsdatum=?
WHERE id = ?
"""

SELECT_COLUMNS = "id, objekttyp, hersteller, modell, seriennummer, einkaufsdatum, aktueller_besitzer, anmerkungen, zuweisungsdatum"


class SQLiteRepository(AbstractRepository):
	"""SQLite-Implementation der Repository-Schnittstelle."""

	def __init__(self, db_path: Path) -> None:
		super().__init__()
		self.db_path = Path(db_path)
		self.connection: Optional[sqlite3.Connection] = None

	def initialize(self) -> None:
		self.connection = sqlite3.connect(self.db_path)
		self.connection.row_factory = sqlite3.Row
		self.connection.execute('PRAGMA foreign_keys = ON')
		self._migrate_schema()
		self.connection.commit()
		self._ensure_default_object_types()

	def _ensure_conn(self) -> sqlite3.Connection:
		if not self.connection:
			raise RepositoryError('SQLite Verbindung nicht initialisiert')
		return self.connection

	def _migrate_schema(self) -> None:
		conn = self._ensure_conn()
		conn.execute(SCHEMA_ITEMS)
		conn.execute(SCHEMA_OBJECT_TYPES)
		columns = [row['name'] for row in conn.execute('PRAGMA table_info(items)')]
		expected = ['id', 'objekttyp', 'hersteller', 'modell', 'seriennummer', 'einkaufsdatum', 'aktueller_besitzer', 'anmerkungen', 'zuweisungsdatum']
		if columns and columns != expected:
			conn.execute('ALTER TABLE items RENAME TO items_old')
			conn.execute(SCHEMA_ITEMS.replace('IF NOT EXISTS ', ''))
			rows = conn.execute('SELECT * FROM items_old').fetchall()
			for row in rows:
				item = Item.from_row(tuple(row))
				conn.execute(
					'INSERT INTO items (id, objekttyp, hersteller, modell, seriennummer, einkaufsdatum, aktueller_besitzer, anmerkungen, zuweisungsdatum) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
					(item.id, item.objekttyp, item.hersteller, item.modell, item.seriennummer, item.einkaufsdatum, item.aktueller_besitzer, item.anmerkungen, item.zuweisungsdatum),
				)
				self._store_object_type(conn, item.objekttyp)
			conn.execute('DROP TABLE items_old')

	def _ensure_default_object_types(self) -> None:
		conn = self._ensure_conn()
		for objekttyp in DEFAULT_OBJECT_TYPES:
			self._store_object_type(conn, objekttyp)
		conn.commit()

	def _store_object_type(self, conn: sqlite3.Connection, objekttyp: str) -> None:
		value = objekttyp.strip()
		if not value:
			return
		conn.execute('INSERT OR IGNORE INTO object_types (name) VALUES (?)', (value,))

	def list(self, filters: Optional[dict] = None) -> List[Item]:
		conn = self._ensure_conn()
		query = f'SELECT {SELECT_COLUMNS} FROM items'
		params: list = []
		if filters:
			conditions = []
			for key, value in filters.items():
				if value in (None, ''):
					continue
				conditions.append(f'{key} LIKE ?')
				params.append(f'%{value}%')
			if conditions:
				query += ' WHERE ' + ' AND '.join(conditions)
		query += ' ORDER BY objekttyp COLLATE NOCASE, hersteller COLLATE NOCASE'
		rows = conn.execute(query, params).fetchall()
		return [Item.from_row(tuple(row)) for row in rows]

	def get(self, item_id: int) -> Optional[Item]:
		conn = self._ensure_conn()
		row = conn.execute(f'SELECT {SELECT_COLUMNS} FROM items WHERE id = ?', (item_id,)).fetchone()
		return Item.from_row(tuple(row)) if row else None

	def create(self, item: Item) -> Item:
		conn = self._ensure_conn()
		self._store_object_type(conn, item.objekttyp)
		cursor = conn.execute(INSERT_ITEM, (
			item.objekttyp,
			item.hersteller,
			item.modell,
			item.seriennummer,
			item.einkaufsdatum,
			item.aktueller_besitzer,
			item.anmerkungen,
			item.zuweisungsdatum,
		))
		conn.commit()
		return item.copy(id=cursor.lastrowid)

	def update(self, item_id: int, item: Item) -> Item:
		conn = self._ensure_conn()
		self._store_object_type(conn, item.objekttyp)
		conn.execute(UPDATE_ITEM, (
			item.objekttyp,
			item.hersteller,
			item.modell,
			item.seriennummer,
			item.einkaufsdatum,
			item.aktueller_besitzer,
			item.anmerkungen,
			item.zuweisungsdatum,
			item_id,
		))
		conn.commit()
		return item.copy(id=item_id)

	def delete(self, item_id: int) -> None:
		conn = self._ensure_conn()
		conn.execute('DELETE FROM items WHERE id = ?', (item_id,))
		conn.commit()

	def distinct_owners(self) -> List[str]:
		conn = self._ensure_conn()
		rows = conn.execute(
			"SELECT DISTINCT aktueller_besitzer FROM items WHERE aktueller_besitzer <> '' ORDER BY aktueller_besitzer COLLATE NOCASE"
		).fetchall()
		return [row[0] for row in rows if row[0]]

	def distinct_object_types(self) -> List[str]:
		conn = self._ensure_conn()
		rows = conn.execute('SELECT name FROM object_types ORDER BY name COLLATE NOCASE').fetchall()
		return [row[0] for row in rows if row[0]]

	def register_object_type(self, objekttyp: str) -> None:
		conn = self._ensure_conn()
		self._store_object_type(conn, objekttyp)
		conn.commit()
