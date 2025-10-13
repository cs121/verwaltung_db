"""Gemeinsame Konstanten und Hilfsfunktionen."""

from __future__ import annotations

from typing import Iterable, List, Optional


DEFAULT_OWNER = "LAGER"


def is_default_owner(value: Optional[str]) -> bool:
        """Prüft, ob der angegebene Besitzer dem Standard "LAGER" entspricht."""

        if value is None:
                return False
        return value.strip().lower() == DEFAULT_OWNER.lower()


def ensure_default_owner(values: Iterable[str]) -> List[str]:
        """Gibt eine bereinigte Liste der Besitzer inklusive des Standardwertes zurück."""

        normalized: dict[str, str] = {}
        for raw in values:
                if raw is None:
                        continue
                text = str(raw).strip()
                if not text:
                        continue
                key = text.lower()
                if key not in normalized:
                        normalized[key] = text

        normalized[DEFAULT_OWNER.lower()] = DEFAULT_OWNER

        ordered = sorted(normalized.values(), key=str.casefold)
        return [DEFAULT_OWNER] + [value for value in ordered if value.lower() != DEFAULT_OWNER.lower()]
