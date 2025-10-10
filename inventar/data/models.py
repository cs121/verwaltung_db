from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class Item:
        """Dataclass repräsentiert einen Inventargegenstand."""

        id: Optional[int] = field(default=None)
        objekttyp: Optional[str] = field(default=None)
        hersteller: Optional[str] = field(default=None)
        modell: Optional[str] = field(default=None)
        seriennummer: Optional[str] = field(default=None)
        einkaufsdatum: Optional[str] = field(default=None)
        zuweisungsdatum: Optional[str] = field(default=None)
        aktueller_besitzer: Optional[str] = field(default=None)
        anmerkungen: Optional[str] = field(default=None)
        stillgelegt: bool = field(default=False)

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
                        'stillgelegt': self.stillgelegt,
                }

        @classmethod
        def from_row(cls, row: dict | tuple) -> Item:
                """Erzeugt ein Item aus einem DB-Row oder Dictionary."""

                if isinstance(row, dict):
                        return cls(
                                id=row.get('id'),
                                objekttyp=cls._normalize(row.get('objekttyp')),
                                hersteller=cls._normalize(row.get('hersteller')),
                                modell=cls._normalize(row.get('modell')),
                                seriennummer=cls._normalize(row.get('seriennummer')),
                                einkaufsdatum=cls._normalize(row.get('einkaufsdatum')),
                                zuweisungsdatum=cls._normalize(row.get('zuweisungsdatum')),
                                aktueller_besitzer=cls._normalize(row.get('aktueller_besitzer')),
                                anmerkungen=cls._normalize(row.get('anmerkungen')),
                                stillgelegt=bool(row.get('stillgelegt', 0)),
                        )
                return cls(
                        id=row[0],
                        objekttyp=cls._normalize(row[1] if len(row) > 1 else None),
                        hersteller=cls._normalize(row[2] if len(row) > 2 else None),
                        modell=cls._normalize(row[3] if len(row) > 3 else None),
                        seriennummer=cls._normalize(row[4] if len(row) > 4 else None),
                        einkaufsdatum=cls._normalize(row[5] if len(row) > 5 else None),
                        zuweisungsdatum=cls._normalize(row[6] if len(row) > 6 else None),
                        aktueller_besitzer=cls._normalize(row[7] if len(row) > 7 else None),
                        anmerkungen=cls._normalize(row[8] if len(row) > 8 else None),
                        stillgelegt=bool(row[9]) if len(row) > 9 else False,
                )

        @staticmethod
        def _normalize(value: Optional[object]) -> Optional[str]:
                if value is None:
                        return None
                text = str(value).strip()
                return text or None

        def copy(self, **updates: object) -> Item:
                """Gibt eine Kopie mit optionalen Updates zurück."""

                data = self.to_dict()
                data.update(updates)
                return Item(**data)

        def with_stillgelegt_note(self) -> Item:
                """Stellt sicher, dass stillgelegte Einträge eine Notiz tragen."""

                if not self.stillgelegt:
                        return self

                note = self.anmerkungen or ""
                if "stillgelegt" in note.lower():
                        # Gleiche Zeichenkette zurückgeben, um unnötige Kopien zu vermeiden.
                        return self if note == self.anmerkungen else self.copy(anmerkungen=note)

                note_stripped = note.strip()
                if note_stripped:
                        separator = "\n" if not note.endswith("\n") else ""
                        updated_note = f"{note}{separator}Stillgelegt"
                else:
                        updated_note = "Stillgelegt"
                return self.copy(anmerkungen=updated_note)


def iso_date_or_today(value: str | None) -> str:
        """Hilfsfunktion um sicher ISO-Daten zu liefern."""

        if value:
                return value
        return date.today().isoformat()
