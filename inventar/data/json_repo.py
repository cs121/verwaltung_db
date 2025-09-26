from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from .models import Item
from .repository import AbstractRepository, RepositoryError


class JSONRepository(AbstractRepository):
	"""JSON-Implementation als Fallback."""

	def __init__(self, json_path: Path) -> None:
		self.json_path = Path(json_path)
		self.items: list[Item] = []

	def initialize(self) -> None:
		if self.json_path.exists():
			self._load()
		else:
			self.items = []
			self._save()

	def _load(self) -> None:
		with self.json_path.open('r', encoding='utf-8') as fh:
			data = json.load(fh)
		self.items = [Item.from_row(entry) for entry in data]

	def _save(self) -> None:
		tmp_path = self.json_path.with_suffix('.tmp')
		with tmp_path.open('w', encoding='utf-8') as fh:
			json.dump([item.to_dict() for item in self.items], fh, ensure_ascii=False, indent=2)
		tmp_path.replace(self.json_path)

	def _next_id(self) -> int:
		return max((item.id or 0 for item in self.items), default=0) + 1

	def list(self, filters: Optional[dict] = None) -> List[Item]:
		if not filters:
			return list(self.items)
		filtered = self.items
		for key, value in filters.items():
			if not value:
				continue
			value_lower = str(value).lower()
			filtered = [item for item in filtered if value_lower in str(getattr(item, key, '')).lower()]
		return filtered

	def get(self, item_id: int) -> Optional[Item]:
		return next((item for item in self.items if item.id == item_id), None)

	def create(self, item: Item) -> Item:
		self.ensure_uniqueness(item.nummer)
		new_item = item.copy(id=self._next_id())
		self.items.append(new_item)
		self._save()
		return new_item

	def update(self, item_id: int, item: Item) -> Item:
		self.ensure_uniqueness(item.nummer, ignore_id=item_id)
		for index, existing in enumerate(self.items):
			if existing.id == item_id:
				self.items[index] = item.copy(id=item_id)
				self._save()
				return self.items[index]
		raise RepositoryError('Item nicht gefunden')

	def delete(self, item_id: int) -> None:
		self.items = [item for item in self.items if item.id != item_id]
		self._save()

	def distinct_owners(self) -> List[str]:
		return sorted({item.aktueller_besitzer for item in self.items if item.aktueller_besitzer})

	def ensure_uniqueness(self, nummer: str, ignore_id: Optional[int] = None) -> None:
		for item in self.items:
			if item.nummer == nummer and item.id != ignore_id:
				raise RepositoryError('Nummer bereits vergeben')
