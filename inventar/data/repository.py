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
        def distinct_object_types(self) -> List[str]:
                """Liefert distinct Objekttypen für die ComboBox."""

        @abc.abstractmethod
        def distinct_manufacturers(self) -> List[str]:
                """Liefert distinct Hersteller für die ComboBox."""

        @abc.abstractmethod
        def distinct_models(self) -> List[str]:
                """Liefert distinct Modelle für die ComboBox."""


class RepositoryFactory:
        """Factory zur Auswahl des passenden Backends."""

        def __init__(self, app_dir: Path | None = None) -> None:
                self.app_dir = app_dir or Path.cwd()
                self.db_path = self.app_dir / 'inventar.db'
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


def create_repository(app_dir: Path | None = None) -> tuple[AbstractRepository, bool]:
        """Convenience-Funktion für Module außerhalb des Datenpakets."""

        factory = RepositoryFactory(app_dir)
        return factory.create()
