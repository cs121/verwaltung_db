from __future__ import annotations

from datetime import datetime
from typing import Dict, Tuple

DATE_FORMAT_DISPLAY = '%d.%m.%Y'
DATE_FORMAT_QT_DISPLAY = 'dd.MM.yyyy'
DATE_FORMAT_STORAGE = '%Y-%m-%d'


class ValidationError(ValueError):
	"""Fehler bei der Validierung eines Items."""


class ItemValidator:
	"""Enthält Validierungslogik für Items."""

	@staticmethod
	def validate(data: Dict[str, object]) -> Tuple[bool, dict]:
		errors: dict[str, str] = {}

		objekttyp = str(data.get('objekttyp', '')).strip()
		if not objekttyp:
			errors['objekttyp'] = 'Objekttyp ist erforderlich'

		for field in ('einkaufsdatum', 'zuweisungsdatum'):
			value = str(data.get(field, '')).strip()
			if value and not ItemValidator._is_valid_date(value):
				errors[field] = 'Ungültiges Datum'

		return len(errors) == 0, errors

	@staticmethod
	def _is_valid_date(value: str) -> bool:
		try:
			datetime.strptime(value, DATE_FORMAT_DISPLAY)
			return True
		except ValueError:
			return False

	@staticmethod
	def convert_display_to_iso(value: str) -> str:
		value = value.strip()
		if not value:
			return ''
		return datetime.strptime(value, DATE_FORMAT_DISPLAY).strftime(DATE_FORMAT_STORAGE)

	@staticmethod
	def convert_iso_to_display(value: str) -> str:
		value = value.strip()
		if not value:
			return ''
		return datetime.strptime(value, DATE_FORMAT_STORAGE).strftime(DATE_FORMAT_DISPLAY)
