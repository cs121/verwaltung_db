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
                        return cls(
                                id=row.get('id'),
                                objekttyp=row.get('objekttyp', ''),
                                hersteller=row.get('hersteller', ''),
                                modell=row.get('modell', ''),
                                seriennummer=row.get('seriennummer', ''),
                                einkaufsdatum=row.get('einkaufsdatum', ''),
                                zuweisungsdatum=row.get('zuweisungsdatum', ''),
                                aktueller_besitzer=row.get('aktueller_besitzer', ''),
                                anmerkungen=row.get('anmerkungen', ''),
                        )
                return cls(
                        id=row[0],
                        objekttyp=row[1],
                        hersteller=row[2],
                        modell=row[3],
                        seriennummer=row[4],
                        einkaufsdatum=row[5],
                        zuweisungsdatum=row[6],
                        aktueller_besitzer=row[7],
                        anmerkungen=row[8],
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
