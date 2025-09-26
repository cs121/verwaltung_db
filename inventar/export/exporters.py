from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable, List

import pandas as pd

from inventar.data.models import Item

COLUMNS = [
	'nummer',
	'objekttyp',
	'hersteller',
	'modell',
	'seriennummer',
	'einkaufsdatum',
	'kaufpreis',
	'aktueller_besitzer',
	'anmerkungen',
]


class ExportError(RuntimeError):
	"""Fehler beim Exportieren der Daten."""


def items_to_dicts(items: Iterable[Item]) -> List[dict]:
	return [item.to_dict() for item in items]


def export_to_csv(items: Iterable[Item], path: Path) -> Path:
	rows = items_to_dicts(items)
	with Path(path).open('w', encoding='utf-8', newline='') as fh:
		writer = csv.DictWriter(fh, fieldnames=COLUMNS)
		writer.writeheader()
		for row in rows:
			writer.writerow({key: row.get(key, '') for key in COLUMNS})
	return Path(path)


def export_to_json(items: Iterable[Item], path: Path) -> Path:
	with Path(path).open('w', encoding='utf-8') as fh:
		json.dump(items_to_dicts(items), fh, ensure_ascii=False, indent=2)
	return Path(path)


def export_to_xlsx(items: Iterable[Item], path: Path) -> Path:
	df = pd.DataFrame(items_to_dicts(items), columns=COLUMNS)
	with pd.ExcelWriter(Path(path), engine='openpyxl') as writer:
		df.to_excel(writer, index=False, sheet_name='Inventar')
	return Path(path)
