from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class Item:
	"""Dataclass repräsentiert einen Inventargegenstand."""

	id: Optional[int] = field(default=None)
	nummer: str = field(default='')
	objekttyp: str = field(default='')
	hersteller: str = field(default='')
	modell: str = field(default='')
	seriennummer: str = field(default='')
	einkaufsdatum: str = field(default='')
	kaufpreis: float = field(default=0.0)
	aktueller_besitzer: str = field(default='')
	anmerkungen: str = field(default='')

	def to_dict(self) -> dict:
		"""Konvertiert das Item in ein Dictionary."""

		return {
			'id': self.id,
			'nummer': self.nummer,
			'objekttyp': self.objekttyp,
			'hersteller': self.hersteller,
			'modell': self.modell,
			'seriennummer': self.seriennummer,
			'einkaufsdatum': self.einkaufsdatum,
			'kaufpreis': self.kaufpreis,
			'aktueller_besitzer': self.aktueller_besitzer,
			'anmerkungen': self.anmerkungen,
		}

	@classmethod
	def from_row(cls, row: dict | tuple) -> Item:
		"""Erzeugt ein Item aus einem DB-Row oder Dictionary."""

		if isinstance(row, dict):
			return cls(**row)
		return cls(
			id=row[0],
			nummer=row[1],
			objekttyp=row[2],
			hersteller=row[3],
			modell=row[4],
			seriennummer=row[5],
			einkaufsdatum=row[6],
			kaufpreis=row[7],
			aktueller_besitzer=row[8],
			anmerkungen=row[9],
		)

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
