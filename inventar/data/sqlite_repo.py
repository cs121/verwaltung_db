from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List, Optional

from .models import Item
from .repository import AbstractRepository, RepositoryError

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	nummer TEXT UNIQUE NOT NULL,
	objekttyp TEXT,
	hersteller TEXT,
	modell TEXT,
	seriennummer TEXT,
	einkaufsdatum TEXT,
	kaufpreis REAL,
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
		self.connection.commit()

	def _ensure_conn(self) -> sqlite3.Connection:
		if not self.connection:
			raise RepositoryError("SQLite Verbindung nicht initialisiert")
		return self.connection

	def list(self, filters: Optional[dict] = None) -> List[Item]:
		conn = self._ensure_conn()
		query = "SELECT * FROM items"
		params: list = []
		if filters:
			conditions = []
			for key, value in filters.items():
				if value is None or value == "":
					continue
				conditions.append(f"{key} LIKE ?")
				params.append(f"%{value}%")
			if conditions:
				query += " WHERE " + " AND ".join(conditions)
		query += " ORDER BY nummer COLLATE NOCASE"
		rows = conn.execute(query, params).fetchall()
		return [Item.from_row(row) for row in rows]

	def get(self, item_id: int) -> Optional[Item]:
		conn = self._ensure_conn()
		row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
		return Item.from_row(row) if row else None

	def create(self, item: Item) -> Item:
		conn = self._ensure_conn()
		self.ensure_uniqueness(item.nummer)
		cursor = conn.execute(
			"""
			INSERT INTO items (
				nummer, objekttyp, hersteller, modell, seriennummer,
				einkaufsdatum, kaufpreis, aktueller_besitzer, anmerkungen
			) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
			""",
			(
				item.nummer,
				item.objekttyp,
				item.hersteller,
				item.modell,
				item.seriennummer,
				item.einkaufsdatum,
				item.kaufpreis,
				item.aktueller_besitzer,
				item.anmerkungen,
			),
		)
		conn.commit()
		return item.copy(id=cursor.lastrowid)

	def update(self, item_id: int, item: Item) -> Item:
		conn = self._ensure_conn()
		self.ensure_uniqueness(item.nummer, ignore_id=item_id)
		conn.execute(
			"""
			UPDATE items SET
				nummer=?, objekttyp=?, hersteller=?, modell=?, seriennummer=?,
				einkaufsdatum=?, kaufpreis=?, aktueller_besitzer=?, anmerkungen=?
			WHERE id = ?
			""",
			(
				item.nummer,
				item.objekttyp,
				item.hersteller,
				item.modell,
				item.seriennummer,
				item.einkaufsdatum,
				item.kaufpreis,
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

	def ensure_uniqueness(self, nummer: str, ignore_id: Optional[int] = None) -> None:
		conn = self._ensure_conn()
		query = "SELECT id FROM items WHERE nummer = ?"
		params: list = [nummer]
		if ignore_id is not None:
			query += " AND id <> ?"
			params.append(ignore_id)
		row = conn.execute(query, params).fetchone()
		if row:
			raise RepositoryError("Nummer bereits vergeben")
