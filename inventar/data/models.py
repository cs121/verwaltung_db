from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class Item:
	"""Dataclass repräsentiert einen Inventargegenstand."""

	id: Optional[int] = field(default=None)
	objekttyp: str = field(default='')
	hersteller: str = field(default='')
	modell: str = field(default='')
	seriennummer: str = field(default='')
	einkaufsdatum: str = field(default='')
	zuweisungsdatum: str = field(default='')
	aktueller_besitzer: str = field(default='')
	anmerkungen: str = field(default='')

	def to_dict(self) -> dict:
		"""Konvertiert das Item in ein Dictionary."""

		return {
			'id': self.id,
			'objekttyp': self.objekttyp,
			'hersteller': self.hersteller,
			'modell': self.modell,
			'seriennummer': self.seriennummer,
			'einkaufsdatum': self.einkaufsdatum,
			'zuweisungsdatum': self.zuweisungsdatum,
			'aktueller_besitzer': self.aktueller_besitzer,
			'anmerkungen': self.anmerkungen,
		}

	@classmethod
	def from_row(cls, row: dict | tuple) -> Item:
		"""Erzeugt ein Item aus einem DB-Row oder Dictionary."""

		if isinstance(row, dict):
			return cls(**cls._normalize_dict(row))
		return cls(**cls._normalize_tuple(row))

	@staticmethod
	def _normalize_dict(data: dict) -> dict:
		"""Gleicht unterschiedliche Datenformate auf das neue Schema an."""

		return {
			'id': data.get('id'),
			'objekttyp': data.get('objekttyp', ''),
			'hersteller': data.get('hersteller', ''),
			'modell': data.get('modell', ''),
			'seriennummer': data.get('seriennummer', ''),
			'einkaufsdatum': data.get('einkaufsdatum', ''),
			'zuweisungsdatum': data.get('zuweisungsdatum', data.get('zuweisung', '')),
			'aktueller_besitzer': data.get('aktueller_besitzer', ''),
			'anmerkungen': data.get('anmerkungen', ''),
		}

	@staticmethod
	def _normalize_tuple(row: tuple) -> dict:
		"""Konvertiert Tupel aus unterschiedlichen Schemas in das neue Format."""

		if len(row) == 9:
			return {
				'id': row[0],
				'objekttyp': row[1],
				'hersteller': row[2],
				'modell': row[3],
				'seriennummer': row[4],
				'einkaufsdatum': row[5],
				'aktueller_besitzer': row[6],
				'anmerkungen': row[7],
				'zuweisungsdatum': row[8] if len(row) > 8 else '',
			}
		# Altes Schema mit nummer/kaufpreis
		return {
			'id': row[0],
			'objekttyp': row[2],
			'hersteller': row[3],
			'modell': row[4],
			'seriennummer': row[5],
			'einkaufsdatum': row[6],
			'aktueller_besitzer': row[8],
			'anmerkungen': row[9] if len(row) > 9 else '',
			'zuweisungsdatum': '',
		}

	def copy(self, **updates: object) -> Item:
		"""Gibt eine Kopie mit optionalen Updates zurück."""

		data = self.to_dict()
		data.update(updates)
		return Item(**data)


def iso_date_or_today(value: str | None) -> str:
	"""Hilfsfunktion um sicher ISO-Daten zu liefern."""

	if value:
		return value
	return date.today().isoformat()
