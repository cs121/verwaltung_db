from __future__ import annotations

import abc
import logging
from pathlib import Path
from typing import List, Optional

from .models import Item

log = logging.getLogger(__name__)


class RepositoryError(RuntimeError):
        """Fehler beim Arbeiten mit einem Repository."""


class AbstractRepository(abc.ABC):
        """Gemeinsame Schnittstelle für den Datenzugriff."""

        @abc.abstractmethod
        def list(self, filters: Optional[dict] = None) -> List[Item]:
                """Listet Items optional gefiltert."""

        @abc.abstractmethod
        def get(self, item_id: int) -> Optional[Item]:
                """Lädt ein Item über die ID."""

        @abc.abstractmethod
        def create(self, item: Item) -> Item:
                """Erzeugt ein neues Item und liefert es mit ID zurück."""

        @abc.abstractmethod
        def update(self, item_id: int, item: Item) -> Item:
                """Aktualisiert ein Item."""

        @abc.abstractmethod
        def delete(self, item_id: int) -> None:
                """Löscht ein Item."""

        @abc.abstractmethod
        def deactivate(self, item_id: int) -> Item:
                """Markiert ein Item als stillgelegt."""

        @abc.abstractmethod
        def distinct_owners(self) -> List[str]:
                """Liefert distinct Besitzer für die ComboBox."""

        @abc.abstractmethod
        def clear_owner(self, owner: str) -> int:
                """Setzt gelöschte Besitzer auf den Standardwert und liefert die Anzahl der Aktualisierungen."""

        @abc.abstractmethod
        def clear_serial_number(self, serial_number: str) -> int:
                """Entfernt eine Seriennummer aus allen Einträgen und liefert die Anzahl der Aktualisierungen."""

        @abc.abstractmethod
        def clear_object_type(self, object_type: str) -> int:
                """Entfernt einen Objekttyp aus allen Einträgen und liefert die Anzahl der Aktualisierungen."""

        @abc.abstractmethod
        def clear_manufacturer(self, manufacturer: str) -> int:
                """Entfernt einen Hersteller aus allen Einträgen und liefert die Anzahl der Aktualisierungen."""

        @abc.abstractmethod
        def clear_model(self, model: str) -> int:
                """Entfernt ein Modell aus allen Einträgen und liefert die Anzahl der Aktualisierungen."""

        @abc.abstractmethod
        def distinct_object_types(self) -> List[str]:
                """Liefert distinct Objekttypen für die ComboBox."""

        @abc.abstractmethod
        def distinct_manufacturers(self) -> List[str]:
                """Liefert distinct Hersteller für die ComboBox."""

        @abc.abstractmethod
        def distinct_models(self) -> List[str]:
                """Liefert distinct Modelle für die ComboBox."""

        @abc.abstractmethod
        def distinct_serial_numbers(self) -> List[str]:
                """Liefert distinct Seriennummern für die ComboBox."""

        @abc.abstractmethod
        def list_custom_values(self, category: str) -> List[str]:
                """Liefert gespeicherte Zusatzwerte für Auswahlfelder."""

        @abc.abstractmethod
        def add_custom_value(self, category: str, value: str) -> None:
                """Speichert einen neuen Zusatzwert für Auswahlfelder."""

        @abc.abstractmethod
        def remove_custom_value(self, category: str, value: str) -> None:
                """Entfernt einen gespeicherten Zusatzwert."""


class RepositoryFactory:
        """Factory zur Auswahl des passenden Backends."""

        def __init__(
                self,
                app_dir: Path | None = None,
                db_path: Path | None = None,
                json_path: Path | None = None,
        ) -> None:
                base_dir = app_dir or Path.cwd()
                if db_path is not None:
                        self.db_path = Path(db_path)
                        base_dir = self.db_path.parent
                else:
                        self.db_path = base_dir / 'inventar.db'
                self.app_dir = base_dir
                if json_path is not None:
                        self.json_path = Path(json_path)
                else:
                        self.json_path = self.app_dir / 'inventar_fallback.json'

        def create(self) -> tuple[AbstractRepository, bool]:
                """Erzeugt ein Repository und kennzeichnet JSON-Fallback."""

                try:
                        from .sqlite_repo import SQLiteRepository

                        repo = SQLiteRepository(self.db_path)
                        repo.initialize()
                        log.info('SQLite Repository initialisiert: %s', self.db_path)
                        return repo, False
                except Exception as exc:  # noqa: BLE001
                        log.exception('SQLite-Initialisierung fehlgeschlagen, Fallback JSON', exc_info=exc)
                        from .json_repo import JSONRepository

                        repo = JSONRepository(self.json_path)
                        repo.initialize()
                        return repo, True


def create_repository(
        app_dir: Path | None = None,
        db_path: Path | None = None,
        json_path: Path | None = None,
) -> tuple[AbstractRepository, bool]:
        """Convenience-Funktion für Module außerhalb des Datenpakets."""

        factory = RepositoryFactory(app_dir=app_dir, db_path=db_path, json_path=json_path)
        return factory.create()
