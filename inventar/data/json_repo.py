
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from .constants import DEFAULT_OBJECT_TYPES
from .models import Item
from .repository import AbstractRepository, RepositoryError


class JSONRepository(AbstractRepository):
	"""JSON-Implementation als Fallback."""

	def __init__(self, json_path: Path) -> None:
		self.json_path = Path(json_path)
		self.items: list[Item] = []
		self.object_types: set[str] = set()

	def initialize(self) -> None:
		if self.json_path.exists():
			self._load()
		else:
			self.items = []
			self.object_types = set(DEFAULT_OBJECT_TYPES)
			self._save()

	def _load(self) -> None:
		with self.json_path.open('r', encoding='utf-8') as fh:
			data = json.load(fh)
		if isinstance(data, dict):
			items_data = data.get('items', [])
			type_data = data.get('object_types', [])
		else:
			items_data = data
			type_data = []
		self.items = [Item.from_row(entry) for entry in items_data]
		self.object_types = {value for value in type_data if value}
		self.object_types.update(DEFAULT_OBJECT_TYPES)
		self.object_types.update(item.objekttyp for item in self.items if item.objekttyp)

	def _save(self) -> None:
		tmp_path = self.json_path.with_suffix('.tmp')
		with tmp_path.open('w', encoding='utf-8') as fh:
			json.dump(
				{
					'items': [item.to_dict() for item in self.items],
					'object_types': sorted(self.object_types),
				},
				fh,
				ensure_ascii=False,
				indent=2,
			)
		tmp_path.replace(self.json_path)

	def _next_id(self) -> int:
		return max((item.id or 0 for item in self.items), default=0) + 1

	def _register_object_type(self, objekttyp: str) -> None:
		value = objekttyp.strip()
		if not value:
			return
		self.object_types.add(value)

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
		new_item = item.copy(id=self._next_id())
		self.items.append(new_item)
		self._register_object_type(new_item.objekttyp)
		self._save()
		return new_item

	def update(self, item_id: int, item: Item) -> Item:
		for index, existing in enumerate(self.items):
			if existing.id == item_id:
				updated = item.copy(id=item_id)
				self.items[index] = updated
				self._register_object_type(updated.objekttyp)
				self._save()
				return updated
		raise RepositoryError('Item nicht gefunden')

	def delete(self, item_id: int) -> None:
		self.items = [item for item in self.items if item.id != item_id]
		self._save()

	def distinct_owners(self) -> List[str]:
		return sorted({item.aktueller_besitzer for item in self.items if item.aktueller_besitzer})

	def distinct_object_types(self) -> List[str]:
		return sorted({value for value in self.object_types if value})

	def register_object_type(self, objekttyp: str) -> None:
		self._register_object_type(objekttyp)
		self._save()
