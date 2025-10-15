"""Import-Hilfen für Inventardaten."""

from __future__ import annotations

import math
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import List

import pandas as pd

from inventar.data.models import Item
from inventar.export.exporters import COLUMNS as EXPORT_COLUMNS

__all__ = [
        "InventoryImportError",
        "ImportResult",
        "import_items",
]


class InventoryImportError(RuntimeError):
        """Fehler beim Öffnen oder Interpretieren einer Quelldatei."""


@dataclass(slots=True)
class ImportResult:
        """Enthält das Ergebnis eines Importvorganges."""

        items: List[Item]
        errors: List[str]


SUPPORTED_SUFFIXES = {
        ".csv",
        ".xlsx",
        ".xlsm",
        ".xls",
}


# Mapping der erlaubten Spaltennamen auf die internen Schlüssel
COLUMN_ALIASES = {
        "objekttyp": "objekttyp",
        "objektart": "objekttyp",
        "type": "objekttyp",
        "hersteller": "hersteller",
        "manufacturer": "hersteller",
        "modell": "modell",
        "model": "modell",
        "seriennummer": "seriennummer",
        "serialnumber": "seriennummer",
        "serial": "seriennummer",
        "einkaufsdatum": "einkaufsdatum",
        "kaufdatum": "einkaufsdatum",
        "purchase_date": "einkaufsdatum",
        "zuweisungsdatum": "zuweisungsdatum",
        "assignment_date": "zuweisungsdatum",
        "aktueller_besitzer": "aktueller_besitzer",
        "besitzer": "aktueller_besitzer",
        "owner": "aktueller_besitzer",
        "anmerkungen": "anmerkungen",
        "notizen": "anmerkungen",
        "notes": "anmerkungen",
        "bemerkungen": "anmerkungen",
        "stillgelegt": "stillgelegt",
        "inactive": "stillgelegt",
        "deaktiviert": "stillgelegt",
}

REQUIRED_COLUMNS = {"objekttyp"}
TEXT_COLUMNS = [
        "objekttyp",
        "hersteller",
        "modell",
        "seriennummer",
        "aktueller_besitzer",
        "anmerkungen",
]
DATE_COLUMNS = ["einkaufsdatum", "zuweisungsdatum"]
BOOLEAN_COLUMNS = ["stillgelegt"]
BOOLEAN_TRUE = {"1", "true", "yes", "ja", "y", "x"}
BOOLEAN_FALSE = {"0", "false", "no", "nein", "n"}
DATE_DISPLAY_FORMATS = ["%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d"]


def import_items(path: Path | str) -> ImportResult:
        """Liest Inventardaten aus der angegebenen Datei ein."""

        source = Path(path)
        if not source.exists():
                raise InventoryImportError(f"Datei nicht gefunden: {source}")
        if source.suffix.lower() not in SUPPORTED_SUFFIXES:
                supported = ", ".join(sorted(SUPPORTED_SUFFIXES))
                raise InventoryImportError(f"Nicht unterstütztes Format: {source.suffix}. Unterstützt: {supported}")

        frame = _read_frame(source)
        if frame.empty:
                return ImportResult(items=[], errors=[])

        prepared = _prepare_frame(frame)
        records = prepared.to_dict(orient="records")
        items: list[Item] = []
        errors: list[str] = []
        for row_number, record in enumerate(records, start=2):
                try:
                        item = _record_to_item(record)
                except ValueError as exc:  # noqa: PERF203 - bewusst je Zeile
                        errors.append(f"Zeile {row_number}: {exc}")
                        continue
                if item is None:
                        continue
                items.append(item)
        return ImportResult(items=items, errors=errors)


def _read_frame(source: Path) -> pd.DataFrame:
        suffix = source.suffix.lower()
        if suffix == ".csv":
                return pd.read_csv(source, dtype=object, keep_default_na=False, na_values=["", "NA", "NaN"])
        return pd.read_excel(source, dtype=object)


def _prepare_frame(frame: pd.DataFrame) -> pd.DataFrame:
        rename_map = {}
        for column in frame.columns:
                canonical = COLUMN_ALIASES.get(_normalize_column_name(str(column)))
                if canonical:
                        rename_map[column] = canonical
        normalized = frame.rename(columns=rename_map)
        missing = [name for name in REQUIRED_COLUMNS if name not in normalized.columns]
        if missing:
                readable = ", ".join(sorted(missing))
                raise InventoryImportError(f"Erforderliche Spalte fehlt: {readable}")

        # Behalte nur die Spalten, die das System kennt
        desired = [col for col in EXPORT_COLUMNS if col in normalized.columns]
        for optional in BOOLEAN_COLUMNS:
                if optional in normalized.columns and optional not in desired:
                        desired.append(optional)
        cleaned = normalized.loc[:, desired].copy()
        cleaned = cleaned.replace({pd.NA: None})
        return cleaned


def _record_to_item(record: dict) -> Item | None:
        data: dict[str, object | None] = {}
        for name in TEXT_COLUMNS:
                raw = record.get(name)
                data[name] = _clean_text(raw)
        for name in DATE_COLUMNS:
                raw = record.get(name)
                try:
                        data[name] = _clean_date(raw)
                except ValueError as exc:
                        raise ValueError(f"Ungültiges Datum in Spalte '{name}': {exc}") from exc
        stillgelegt = False
        if "stillgelegt" in record:
                raw = record.get("stillgelegt")
                try:
                        stillgelegt = _clean_bool(raw)
                except ValueError as exc:
                        raise ValueError(f"Ungültiger Wahrheitswert für 'stillgelegt': {exc}") from exc
        data["stillgelegt"] = stillgelegt

        if not _has_meaningful_content(data):
                return None

        item = Item(
                objekttyp=data.get("objekttyp"),
                hersteller=data.get("hersteller"),
                modell=data.get("modell"),
                seriennummer=data.get("seriennummer"),
                einkaufsdatum=data.get("einkaufsdatum"),
                zuweisungsdatum=data.get("zuweisungsdatum"),
                aktueller_besitzer=data.get("aktueller_besitzer"),
                anmerkungen=data.get("anmerkungen"),
                stillgelegt=bool(data.get("stillgelegt", False)),
        )
        return item


def _clean_text(value: object | None) -> str | None:
        if value is None:
                return None
        if isinstance(value, str):
                text = value.strip()
                return text or None
        if isinstance(value, int):
                return str(value)
        if isinstance(value, float):
                if math.isnan(value):
                        return None
                if float(value).is_integer():
                        return str(int(value))
                return str(value).strip()
        if isinstance(value, (datetime, date)):
                return value.isoformat()
        text = str(value).strip()
        return text or None


def _clean_date(value: object | None) -> str | None:
        if value is None:
                return None
        if isinstance(value, str):
                text = value.strip()
                if not text:
                        return None
                for fmt in DATE_DISPLAY_FORMATS:
                        try:
                                parsed = datetime.strptime(text, fmt)
                                return parsed.date().isoformat()
                        except ValueError:
                                continue
        try:
                parsed = pd.to_datetime(value, dayfirst=True, errors="raise")
        except Exception as exc:  # noqa: BLE001
                raise ValueError(str(value)) from exc
        if pd.isna(parsed):
                return None
        if isinstance(parsed, pd.Timestamp):
                return parsed.date().isoformat()
        if isinstance(parsed, datetime):
                return parsed.date().isoformat()
        if isinstance(parsed, date):
                return parsed.isoformat()
        return None


def _clean_bool(value: object | None) -> bool:
        if value is None:
                return False
        if isinstance(value, bool):
                return value
        if isinstance(value, (int, float)):
                return float(value) != 0
        text = str(value).strip().lower()
        if not text:
                return False
        if text in BOOLEAN_TRUE:
                return True
        if text in BOOLEAN_FALSE:
                return False
        raise ValueError(str(value))


def _normalize_column_name(name: str) -> str:
        normalized = unicodedata.normalize("NFKD", name)
        normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
        normalized = normalized.replace("-", "_").replace(" ", "_")
        while "__" in normalized:
                normalized = normalized.replace("__", "_")
        return normalized.lower().strip()


def _has_meaningful_content(data: dict[str, object | None]) -> bool:
        keys = [
                "objekttyp",
                "hersteller",
                "modell",
                "seriennummer",
                "einkaufsdatum",
                "zuweisungsdatum",
                "aktueller_besitzer",
                "anmerkungen",
        ]
        for key in keys:
                value = data.get(key)
                if isinstance(value, str) and value.strip():
                        return True
                if value not in (None, ""):
                        return True
        return bool(data.get("stillgelegt"))
