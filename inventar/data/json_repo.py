from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List, Optional

from .models import Item
from .repository import AbstractRepository, RepositoryError
from ..utils.constants import DEFAULT_OWNER


class JSONRepository(AbstractRepository):
        """JSON-Implementation als Fallback."""

        def __init__(self, json_path: Path) -> None:
                self.json_path = Path(json_path)
                self.items: list[Item] = []
                self.custom_values: dict[str, list[str]] = {}

        def initialize(self) -> None:
                if self.json_path.exists():
                        self._load()
                else:
                        self.items = []
                        self.custom_values = {}
                        self._save()

        def _load(self) -> None:
                with self.json_path.open('r', encoding='utf-8') as fh:
                        data = json.load(fh)
                if isinstance(data, list):
                        self.items = [Item.from_row(entry) for entry in data]
                        self.custom_values = {}
                        return
                items_data = data.get('items', []) if isinstance(data, dict) else []
                custom_data = data.get('custom_values', {}) if isinstance(data, dict) else {}
                self.items = [Item.from_row(entry) for entry in items_data]
                self.custom_values = {
                        str(category): self._normalize_values(values)
                        for category, values in custom_data.items()
                }

        def _save(self) -> None:
                tmp_path = self.json_path.with_suffix('.tmp')
                with tmp_path.open('w', encoding='utf-8') as fh:
                        payload = {
                                'items': [item.to_dict() for item in self.items],
                                'custom_values': self.custom_values,
                        }
                        json.dump(payload, fh, ensure_ascii=False, indent=2)
                tmp_path.replace(self.json_path)

        def _next_id(self) -> int:
                return max((item.id or 0 for item in self.items), default=0) + 1

        def list(self, filters: Optional[dict] = None) -> List[Item]:
                self._ensure_stillgelegt_notes()
                items = list(self.items)
                if filters is None:
                        return self._sorted_items(item.with_stillgelegt_note() for item in items)

                filters_copy = dict(filters)
                global_search = filters_copy.pop('__global__', None)
                filtered = items
                for key, value in filters_copy.items():
                        if not value:
                                continue
                        value_lower = str(value).lower()
                        filtered = [item for item in filtered if value_lower in str(getattr(item, key, '')).lower()]

                if global_search:
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
                        search_lower = str(global_search).lower()

                        def matches_any_field(item: Item) -> bool:
                                return any(
                                        search_lower in str(getattr(item, key, '')).lower()
                                        for key in allowed_keys
                                )

                        filtered = [item for item in filtered if matches_any_field(item)]

                return self._sorted_items(item.with_stillgelegt_note() for item in filtered)

        @staticmethod
        def _sorted_items(items: Iterable[Item]) -> List[Item]:
                prepared = [item if isinstance(item, Item) else Item.from_row(item) for item in items]
                return sorted(
                        prepared,
                        key=lambda item: (
                                (item.objekttyp or '').lower(),
                                (item.modell or '').lower(),
                        ),
                )

        def _ensure_stillgelegt_notes(self) -> None:
                changed = False
                for index, item in enumerate(self.items):
                        updated_item = item.with_stillgelegt_note()
                        if updated_item.anmerkungen != item.anmerkungen:
                                self.items[index] = updated_item
                                changed = True
                if changed:
                        self._save()

        def get(self, item_id: int) -> Optional[Item]:
                item = next((item for item in self.items if item.id == item_id), None)
                return item.with_stillgelegt_note() if item else None

        def create(self, item: Item) -> Item:
                item = item.with_stillgelegt_note()
                new_item = item.copy(id=self._next_id())
                self.items.append(new_item)
                self._save()
                return new_item

        def update(self, item_id: int, item: Item) -> Item:
                item = item.with_stillgelegt_note()
                for index, existing in enumerate(self.items):
                        if existing.id == item_id:
                                self.items[index] = item.copy(id=item_id)
                                self._save()
                                return self.items[index]
                raise RepositoryError('Item nicht gefunden')

        def delete(self, item_id: int) -> None:
                self.items = [item for item in self.items if item.id != item_id]
                self._save()

        def deactivate(self, item_id: int) -> Item:
                for index, existing in enumerate(self.items):
                        if existing.id == item_id:
                                updated = existing.copy(stillgelegt=True).with_stillgelegt_note()
                                self.items[index] = updated
                                self._save()
                                return updated
                raise RepositoryError('Item nicht gefunden')

        def distinct_owners(self) -> List[str]:
                return sorted({
                        item.aktueller_besitzer
                        for item in self.items
                        if item.aktueller_besitzer
                })

        def clear_owner(self, owner: str) -> int:
                owner = owner.strip()
                if not owner or owner.lower() == DEFAULT_OWNER.lower():
                        return 0
                updated = 0
                for index, item in enumerate(self.items):
                        if item.aktueller_besitzer == owner:
                                self.items[index] = item.copy(aktueller_besitzer=DEFAULT_OWNER)
                                updated += 1
                if updated:
                        self._save()
                return updated

        def clear_serial_number(self, serial_number: str) -> int:
                serial_number = serial_number.strip()
                if not serial_number:
                        return 0
                updated = 0
                for index, item in enumerate(self.items):
                        if item.seriennummer == serial_number:
                                self.items[index] = item.copy(seriennummer='')
                                updated += 1
                if updated:
                        self._save()
                return updated

        def clear_object_type(self, object_type: str) -> int:
                object_type = object_type.strip()
                if not object_type:
                        return 0
                updated = 0
                for index, item in enumerate(self.items):
                        if item.objekttyp == object_type:
                                self.items[index] = item.copy(objekttyp='')
                                updated += 1
                if updated:
                        self._save()
                return updated

        def clear_manufacturer(self, manufacturer: str) -> int:
                manufacturer = manufacturer.strip()
                if not manufacturer:
                        return 0
                updated = 0
                for index, item in enumerate(self.items):
                        if item.hersteller == manufacturer:
                                self.items[index] = item.copy(hersteller='')
                                updated += 1
                if updated:
                        self._save()
                return updated

        def clear_model(self, model: str) -> int:
                model = model.strip()
                if not model:
                        return 0
                updated = 0
                for index, item in enumerate(self.items):
                        if item.modell == model:
                                self.items[index] = item.copy(modell='')
                                updated += 1
                if updated:
                        self._save()
                return updated

        def distinct_object_types(self) -> List[str]:
                return sorted({
                        item.objekttyp
                        for item in self.items
                        if item.objekttyp
                })

        def distinct_manufacturers(self) -> List[str]:
                return sorted({
                        item.hersteller
                        for item in self.items
                        if item.hersteller
                })

        def distinct_models(self) -> List[str]:
                return sorted({
                        item.modell
                        for item in self.items
                        if item.modell
                })

        def distinct_serial_numbers(self) -> List[str]:
                return sorted({
                        item.seriennummer
                        for item in self.items
                        if item.seriennummer
                })

        @staticmethod
        def _normalize_values(values: Iterable[str]) -> list[str]:
                seen: set[str] = set()
                normalized: list[str] = []
                for value in values:
                        text = str(value).strip()
                        if not text:
                                continue
                        key = text.lower()
                        if key in seen:
                                continue
                        seen.add(key)
                        normalized.append(text)
                normalized.sort(key=str.casefold)
                return normalized

        def list_custom_values(self, category: str) -> List[str]:
                return list(self.custom_values.get(category, []))

        def add_custom_value(self, category: str, value: str) -> None:
                normalized = self._normalize_values(self.custom_values.get(category, []) + [value])
                self.custom_values[category] = normalized
                self._save()

        def remove_custom_value(self, category: str, value: str) -> None:
                values = [entry for entry in self.custom_values.get(category, []) if entry.lower() != value.lower()]
                if values:
                        self.custom_values[category] = self._normalize_values(values)
                elif category in self.custom_values:
                        del self.custom_values[category]
                self._save()
