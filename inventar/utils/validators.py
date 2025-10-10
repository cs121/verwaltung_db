from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional, Tuple

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

                einkaufsdatum = str(data.get('einkaufsdatum', '')).strip()
                if einkaufsdatum:
                        if not ItemValidator._is_valid_date(einkaufsdatum):
                                errors['einkaufsdatum'] = 'Ungültiges Datum'

                zuweisungsdatum = str(data.get('zuweisungsdatum', '')).strip()
                if zuweisungsdatum:
                        if not ItemValidator._is_valid_date(zuweisungsdatum):
                                errors['zuweisungsdatum'] = 'Ungültiges Datum'

                return len(errors) == 0, errors

        @staticmethod
        def _is_valid_date(value: str) -> bool:
                try:
                        datetime.strptime(value, DATE_FORMAT_DISPLAY)
                        return True
                except ValueError:
                        return False

        @staticmethod
        def convert_display_to_iso(value: Optional[str]) -> str:
                if value is None:
                        return ''
                value = value.strip()
                if not value:
                        return ''
                return datetime.strptime(value, DATE_FORMAT_DISPLAY).strftime(DATE_FORMAT_STORAGE)

        @staticmethod
        def convert_iso_to_display(value: Optional[str]) -> str:
                if value is None:
                        return ''
                value = value.strip()
                if not value:
                        return ''
                return datetime.strptime(value, DATE_FORMAT_STORAGE).strftime(DATE_FORMAT_DISPLAY)
