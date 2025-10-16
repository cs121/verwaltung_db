from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, QTimer
from PySide6.QtGui import QAction, QActionGroup, QIcon, QKeySequence, QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QInputDialog,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QRadioButton,
    QPushButton,
    QSizePolicy,
    QStatusBar,
    QTableView,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from inventar.data.models import Item
from inventar.data.repository import RepositoryError, create_repository
from inventar.export.exporters import export_to_csv, export_to_json, export_to_xlsx
from inventar.importers import InventoryImportError, import_items
from inventar.ui.item_dialog import ItemDialog
from inventar.ui.print import TablePrinter
from inventar.utils.constants import DEFAULT_OWNER, ensure_default_owner, is_default_owner
from inventar.utils.settings import SettingsManager
from inventar.utils.theme_manager import ThemeManager
from inventar.utils.validators import DATE_FORMAT_DISPLAY, ItemValidator


HEADERS = [
        "Objekttyp",
        "Hersteller",
        "Modell",
        "Seriennummer",
        "Einkaufsdatum",
        "Zuweisungsdatum",
        "Aktueller Besitzer",
        "Anmerkungen",
]

COLUMN_KEYS = [
        "objekttyp",
        "hersteller",
        "modell",
        "seriennummer",
        "einkaufsdatum",
        "zuweisungsdatum",
        "aktueller_besitzer",
        "anmerkungen",
]

CUSTOM_CATEGORY_MANUFACTURER = "manufacturer"
CUSTOM_CATEGORY_MODEL = "model"
CUSTOM_CATEGORY_SERIAL = "serial_number"
CUSTOM_CATEGORY_OWNER = "owner"


class ItemTableModel(QAbstractTableModel):
        """TableModel für Inventaritems."""

        def __init__(self, items: Optional[List[Item]] = None) -> None:
                super().__init__()
                self._items: List[Item] = items or []

        def set_items(self, items: List[Item]) -> None:
                self.beginResetModel()
                self._items = list(items)
                self.endResetModel()

        def sort(self, column: int, order: Qt.SortOrder = Qt.AscendingOrder) -> None:  # type: ignore[override]
                if not 0 <= column < len(COLUMN_KEYS):
                        return

                key = COLUMN_KEYS[column]
                reverse = order == Qt.DescendingOrder

                def build_sort_key(item: Item):
                        value = getattr(item, key)
                        if key in {"einkaufsdatum", "zuweisungsdatum"}:
                                if value:
                                        try:
                                                return (0, datetime.strptime(value, "%Y-%m-%d"))
                                        except ValueError:
                                                return (1, str(value))
                                return (2, datetime.min)
                        if isinstance(value, str):
                                return (0, value.lower())
                        if value is None:
                                return (1, "")
                        return (0, value)

                self.layoutAboutToBeChanged.emit()
                try:
                        self._items.sort(key=build_sort_key, reverse=reverse)
                finally:
                        self.layoutChanged.emit()

        def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # type: ignore[override]
                return 0 if parent.isValid() else len(self._items)

        def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # type: ignore[override]
                return 0 if parent.isValid() else len(COLUMN_KEYS)

        def data(self, index: QModelIndex, role: int = Qt.DisplayRole):  # type: ignore[override]
                if not index.isValid():
                        return None
                item = self._items[index.row()]
                key = COLUMN_KEYS[index.column()]
                value = getattr(item, key)
                if role == Qt.DisplayRole:
                        if key in {'einkaufsdatum', 'zuweisungsdatum'} and value:
                                return datetime.strptime(value, '%Y-%m-%d').strftime(DATE_FORMAT_DISPLAY)
                        return value
                if role == Qt.UserRole:
                        return item
                if role == Qt.ForegroundRole and getattr(item, 'stillgelegt', False):
                        return QColor(Qt.red)
                if role == Qt.BackgroundRole and getattr(item, 'stillgelegt', False):
                        return QColor(255, 205, 210)
                return None

        def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):  # type: ignore[override]
                if role != Qt.DisplayRole:
                        return None
                if orientation == Qt.Horizontal:
                        return HEADERS[section]
                return section + 1

        def item_at(self, row: int) -> Optional[Item]:
                if 0 <= row < len(self._items):
                        return self._items[row]
                return None


class MainWindow(QMainWindow):
        """Hauptfenster der Inventarverwaltung."""

        def __init__(self) -> None:
                super().__init__()
                self.setWindowTitle('Inventarliste Version 1.0')
                self.resize(1280, 720)

                self.settings = SettingsManager()
                self.theme_manager = ThemeManager()
                default_db_path = Path.cwd() / 'inventar.db'
                self.database_path = self.settings.load_database_path(default_db_path)
                self.repository, self.using_json_fallback = create_repository(db_path=self.database_path)
                self.object_types: List[str] = self.settings.load_object_types()
                self.custom_manufacturers: list[str] = self.repository.list_custom_values(
                        CUSTOM_CATEGORY_MANUFACTURER
                )
                self.custom_models: list[str] = self.repository.list_custom_values(CUSTOM_CATEGORY_MODEL)
                self.custom_serial_numbers: list[str] = self.repository.list_custom_values(CUSTOM_CATEGORY_SERIAL)
                self.custom_owners: list[str] = self.repository.list_custom_values(CUSTOM_CATEGORY_OWNER)
                self.table_model = ItemTableModel()
                self.table = QTableView()
                self.table.setModel(self.table_model)
                self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
                self.table.setSelectionMode(QAbstractItemView.SingleSelection)
                self.table.doubleClicked.connect(self.edit_selected_item)
                self.table.setSortingEnabled(True)

                # RESPONSIVE DESIGN: Tabelle passt sich der Breite an
                self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
                self.table.horizontalHeader().setStretchLastSection(True)

                self.table.setAlternatingRowColors(True)
                self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

                self.printer = TablePrinter(self)

                self._font_size = 10
                self.items: List[Item] = []
                self.filtered_items: List[Item] = []

                self._filter_timer = QTimer(self)
                self._filter_timer.setSingleShot(True)
                self._filter_timer.setInterval(250)
                self._filter_timer.timeout.connect(self.apply_filters)

                self._build_ui()
                self._create_menus()
                self._apply_color_palette()
                self._create_actions()
                self._connect_signals()
                self._load_items()
                self.settings.restore_geometry(self)
                try:
                        self._font_size = self.settings.restore_table(self.table)
                except Exception:
                        pass
                self._update_status()

                if self.using_json_fallback:
                        self.statusBar().showMessage('JSON-Fallback aktiv – SQLite nicht verfügbar', 10000)

        # ---------- UI Aufbau ----------
        def _build_ui(self) -> None:
                central = QWidget(self)
                central.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                layout = QVBoxLayout(central)
                layout.setContentsMargins(10, 10, 10, 10)

                layout.addWidget(self._build_search_box())
                layout.addWidget(self._build_form_filters())

                actions_layout = QHBoxLayout()
                self.new_button = QPushButton('Neues Objekt')
                self.toggle_stillgelegt_button = QRadioButton()
                self.toggle_stillgelegt_button.setChecked(False)
                self._update_stillgelegt_toggle_label(False)
                self.print_button = QPushButton()
                self.print_button.setIcon(QIcon.fromTheme('document-print'))
                self.print_button.setToolTip('Drucken (Ctrl+P)')

                actions_layout.addWidget(self.new_button)
                actions_layout.addWidget(self.toggle_stillgelegt_button)
                actions_layout.addStretch()

                layout.addLayout(actions_layout)

                # RESPONSIVE: Tabelle mit maximaler Ausdehnung
                layout.addWidget(self.table, stretch=1)

                bottom_layout = QHBoxLayout()
                bottom_layout.addWidget(self.print_button)
                bottom_layout.addStretch()
                self.user_count_label = QLabel('User gesamt: 0')
                self.lager_count_label = QLabel('Geräte im Lager: 0')
                bottom_layout.addWidget(self.user_count_label)
                bottom_layout.addSpacing(12)
                bottom_layout.addWidget(self.lager_count_label)
                bottom_layout.addSpacing(12)
                self.current_owner_label = QLabel('Aktueller Besitzer: –')
                bottom_layout.addWidget(self.current_owner_label)
                layout.addLayout(bottom_layout)

                self.status_bar = QStatusBar()
                self.setStatusBar(self.status_bar)

                self.setCentralWidget(central)

        def _create_menus(self) -> None:
                menu_bar = self.menuBar()
                self.file_menu = menu_bar.addMenu('Datei')

                self.open_database_action = QAction('Datenbank auswählen …', self)
                self.file_menu.addAction(self.open_database_action)

                self.backup_database_action = QAction('Datenbank sichern …', self)
                self.file_menu.addAction(self.backup_database_action)

                self.file_menu.addSeparator()
                self.import_action = QAction('Daten importieren …', self)
                self.import_action.setShortcut(QKeySequence('Ctrl+I'))
                self.file_menu.addAction(self.import_action)

                self.export_menu = self.file_menu.addMenu('Daten exportieren')
                export_menu_action = self.export_menu.menuAction()
                export_menu_action.setShortcut(QKeySequence('Ctrl+E'))
                export_menu_action.triggered.connect(self._show_export_menu)
                self.export_excel_action = self.export_menu.addAction('Excel')
                self.export_csv_action = self.export_menu.addAction('CSV')
                self.export_json_action = self.export_menu.addAction('JSON')

                self.file_menu.addSeparator()
                self.theme_menu = self.file_menu.addMenu('Theme auswählen')
                self._populate_theme_menu()

                self.file_menu.addSeparator()
                self.exit_action = QAction('Beenden', self)
                self.file_menu.addAction(self.exit_action)

        def _populate_theme_menu(self) -> None:
                if not hasattr(self, 'theme_menu'):
                        return
                self.theme_menu.clear()
                self.theme_action_group = QActionGroup(self)
                self.theme_action_group.setExclusive(True)
                current = self.theme_manager.active_theme_name
                for name in self.theme_manager.theme_names():
                        action = QAction(name, self)
                        action.setCheckable(True)
                        if name == current:
                                action.setChecked(True)
                        self.theme_action_group.addAction(action)
                        self.theme_menu.addAction(action)
                        action.triggered.connect(lambda checked, theme=name: self._handle_theme_changed(theme) if checked else None)

        def _update_theme_action_checks(self, theme_name: str) -> None:
                if not hasattr(self, 'theme_action_group'):
                        return
                for action in self.theme_action_group.actions():
                        action.setChecked(action.text() == theme_name)

        def _choose_database_path(self) -> None:
                current_path = getattr(self, 'database_path', Path.cwd() / 'inventar.db')
                dialog_caption = 'Speicherort der Datenbank wählen'
                file_filter = 'SQLite-Datenbank (*.db);;Alle Dateien (*)'
                selected, _ = QFileDialog.getSaveFileName(
                        self,
                        dialog_caption,
                        str(current_path),
                        file_filter,
                )
                if not selected:
                        return
                new_path = Path(selected)
                if new_path.suffix == '':
                        new_path = new_path.with_suffix('.db')
                if new_path == current_path:
                        return
                if not self._prepare_for_repository_switch():
                        return
                try:
                        new_path.parent.mkdir(parents=True, exist_ok=True)
                except OSError as exc:
                        QMessageBox.critical(self, 'Fehler', f'Datenbankpfad konnte nicht erstellt werden:\n{exc}')
                        return
                try:
                        repository, using_json_fallback = create_repository(db_path=new_path)
                except Exception as exc:  # noqa: BLE001
                        QMessageBox.critical(self, 'Fehler', f'Datenbank konnte nicht geöffnet werden:\n{exc}')
                        return

                self.database_path = new_path
                self.repository = repository
                self.using_json_fallback = using_json_fallback
                self.settings.save_database_path(self.database_path)
                self._load_items()
                self.reset_filters()
                message = f'Datenbankpfad geändert: {self.database_path}'
                if self.using_json_fallback:
                        message += ' – JSON-Fallback aktiv'
                self.statusBar().showMessage(message, 10000)

        def _prepare_for_repository_switch(self) -> bool:
                """Reset the UI state before switching to another repository."""

                if not getattr(self, 'items', []):
                        return True
                confirm = QMessageBox.question(
                        self,
                        'Datenbank wechseln',
                        'Nicht gespeicherte Änderungen werden verworfen. Möchten Sie fortfahren?',
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No,
                )
                if confirm != QMessageBox.Yes:
                        return False

                self.items = []
                self.filtered_items = []
                self.table_model.set_items([])
                self._update_status()
                return True

        def _backup_database(self) -> None:
                source_path: Optional[Path]
                if self.using_json_fallback and hasattr(self.repository, 'json_path'):
                        source_path = Path(getattr(self.repository, 'json_path'))
                else:
                        source_path = getattr(self, 'database_path', None)
                if not source_path or not source_path.exists():
                        QMessageBox.warning(self, 'Datenbank sichern', 'Keine Datenbankdatei gefunden, die gesichert werden kann.')
                        return

                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                default_name = f"{source_path.stem}_backup_{timestamp}{source_path.suffix}"
                target, _ = QFileDialog.getSaveFileName(
                        self,
                        'Datenbank sichern',
                        str(source_path.with_name(default_name)),
                        'Alle Dateien (*)',
                )
                if not target:
                        return

                target_path = Path(target)
                try:
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                except OSError as exc:
                        QMessageBox.critical(self, 'Datenbank sichern', f'Zielordner konnte nicht erstellt werden:\n{exc}')
                        return

                try:
                        shutil.copy2(source_path, target_path)
                except OSError as exc:
                        QMessageBox.critical(self, 'Datenbank sichern', f'Datenbank konnte nicht gesichert werden:\n{exc}')
                        return

                self.statusBar().showMessage(f'Datenbank erfolgreich gesichert: {target_path}', 8000)

        def _apply_color_palette(self) -> None:
                """Apply the selected color palette to the main window widgets."""
                self.setStyleSheet(self.theme_manager.stylesheet())

        def _handle_theme_changed(self, theme_name: str) -> None:
                if not theme_name:
                        return
                if self.theme_manager.set_active_theme(theme_name):
                        self._apply_color_palette()
                        self._update_theme_action_checks(theme_name)

        def _build_search_box(self) -> QWidget:
                box = QGroupBox('Suchen')
                box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                layout = QHBoxLayout(box)
                self.search_field = QLineEdit()
                self.search_field.setPlaceholderText('In allen Feldern suchen ...')
                self.search_field.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                self.search_field.installEventFilter(self)

                layout.addWidget(self.search_field)
                return box

        def _build_form_filters(self) -> QWidget:
                box = QGroupBox('Filter')
                box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                layout = QHBoxLayout(box)

                left_layout = QFormLayout()
                self.filter_objekttyp = QComboBox()
                self.filter_objekttyp.setEditable(True)
                self.filter_objekttyp.setInsertPolicy(QComboBox.NoInsert)
                self.filter_objekttyp.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                self._update_object_type_filter()

                self.filter_hersteller = QComboBox()
                self.filter_hersteller.setEditable(True)
                self.filter_hersteller.setInsertPolicy(QComboBox.NoInsert)
                self.filter_hersteller.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                self._update_manufacturer_filter()

                self.filter_modell = QComboBox()
                self.filter_modell.setEditable(True)
                self.filter_modell.setInsertPolicy(QComboBox.NoInsert)
                self.filter_modell.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                self._update_model_filter()

                self.filter_seriennummer = QComboBox()
                self.filter_seriennummer.setEditable(True)
                self.filter_seriennummer.setInsertPolicy(QComboBox.NoInsert)
                self.filter_seriennummer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                self._update_serial_filter()

                left_layout.addRow('Objekttyp', self.filter_objekttyp)
                left_layout.addRow('Hersteller', self.filter_hersteller)
                left_layout.addRow('Modell', self.filter_modell)
                left_layout.addRow('Seriennummer', self.filter_seriennummer)

                right_layout = QFormLayout()
                self.filter_besitzer = QComboBox()
                self.filter_besitzer.setEditable(True)
                self.filter_besitzer.setInsertPolicy(QComboBox.NoInsert)
                self.filter_besitzer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                self._update_owner_combo()
                self.filter_anmerkungen = QLineEdit()
                self.filter_anmerkungen.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                self.add_owner_button = QToolButton()
                self.add_owner_button.setText('+')
                self.add_owner_button.setToolTip('Besitzer zur Auswahlliste hinzufügen')
                self.remove_owner_button = QToolButton()
                self.remove_owner_button.setText('−')
                self.remove_owner_button.setToolTip('Ausgewählten Besitzer aus allen Einträgen entfernen')
                owner_layout = QHBoxLayout()
                owner_layout.addWidget(self.filter_besitzer)
                owner_layout.addWidget(self.add_owner_button)
                owner_layout.addWidget(self.remove_owner_button)
                owner_layout.setContentsMargins(0, 0, 0, 0)
                owner_layout.setSpacing(4)
                owner_layout.setStretch(0, 1)
                right_layout.addRow('Aktueller Besitzer', owner_layout)
                right_layout.addRow('Anmerkungen', self.filter_anmerkungen)

                combo_boxes = [
                        self.filter_objekttyp,
                        self.filter_hersteller,
                        self.filter_modell,
                        self.filter_seriennummer,
                        self.filter_besitzer,
                ]

                max_width = max(combo.sizeHint().width() for combo in combo_boxes)
                for combo in combo_boxes:
                        combo.setMinimumWidth(max_width)
                        combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

                layout.addLayout(left_layout)
                layout.addLayout(right_layout)

                self._style_form_labels(left_layout)
                self._style_form_labels(right_layout)

                return box

        @staticmethod
        def _style_form_labels(layout: QFormLayout) -> None:
                """Apply the required style to the labels in a form layout."""
                for row in range(layout.rowCount()):
                        item = layout.itemAt(row, QFormLayout.LabelRole)
                        if not item:
                                continue
                        label = item.widget()
                        if label is None:
                                continue
                        label.setStyleSheet('font-weight: 600;')

        # ---------- Aktionen & Signale ----------
        def _create_actions(self) -> None:
                self.new_action = QAction('Neu', self)
                self.new_action.setShortcut(QKeySequence.New)
                self.edit_action = QAction('Bearbeiten', self)
                self.edit_action.setShortcuts([
                        QKeySequence(Qt.Key_F2),
                        QKeySequence('Ctrl+Shift+E'),
                ])
                self.delete_action = QAction('Löschen', self)
                self.delete_action.setShortcut(QKeySequence.Delete)
                self.search_action = QAction('Suche', self)
                self.search_action.setShortcut(QKeySequence.Find)
                self.print_action = QAction('Drucken', self)
                self.print_action.setShortcut(QKeySequence.Print)

                actions = [
                        self.new_action,
                        self.edit_action,
                        self.delete_action,
                        self.search_action,
                        self.print_action,
                ]
                if hasattr(self, 'import_action'):
                        actions.append(self.import_action)
                for action in actions:
                        self.addAction(action)

        def _connect_signals(self) -> None:
                self.new_button.clicked.connect(self.create_item)
                self.export_excel_action.triggered.connect(lambda: self.export_data('xlsx'))
                self.export_csv_action.triggered.connect(lambda: self.export_data('csv'))
                self.export_json_action.triggered.connect(lambda: self.export_data('json'))
                self.print_button.clicked.connect(self.print_items)
                self.open_database_action.triggered.connect(self._choose_database_path)
                self.backup_database_action.triggered.connect(self._backup_database)
                self.exit_action.triggered.connect(QApplication.quit)

                self.search_field.returnPressed.connect(self._handle_search_submit)
                self.search_field.textChanged.connect(self._handle_search_text_change)
                self.toggle_stillgelegt_button.toggled.connect(self._handle_toggle_stillgelegt)

                self.add_owner_button.clicked.connect(self._add_owner_filter_value)
                self.remove_owner_button.clicked.connect(self._remove_owner_filter_value)
                self.new_action.triggered.connect(self.create_item)
                if hasattr(self, 'import_action'):
                        self.import_action.triggered.connect(self.import_data_from_file)
                self.edit_action.triggered.connect(self.edit_selected_item)
                self.delete_action.triggered.connect(self.delete_selected_item)
                self.search_action.triggered.connect(lambda: self.search_field.setFocus())
                self.print_action.triggered.connect(self.print_items)

        def _show_export_menu(self) -> None:
                if not hasattr(self, 'export_menu'):
                        return
                menu_bar = self.menuBar()
                export_action = self.export_menu.menuAction()
                action_rect = menu_bar.actionGeometry(export_action)
                if action_rect.isValid():
                        popup_position = menu_bar.mapToGlobal(action_rect.bottomLeft())
                else:
                        popup_position = menu_bar.mapToGlobal(menu_bar.rect().bottomLeft())
                menu_bar.setActiveAction(export_action)
                self.export_menu.popup(popup_position)

                if self.filter_hersteller.lineEdit():
                        self.filter_hersteller.lineEdit().returnPressed.connect(self.apply_filters)
                        self.filter_hersteller.lineEdit().textEdited.connect(self._schedule_filter_update)
                self.filter_hersteller.currentIndexChanged.connect(self._schedule_filter_update)
                if self.filter_modell.lineEdit():
                        self.filter_modell.lineEdit().returnPressed.connect(self.apply_filters)
                        self.filter_modell.lineEdit().textEdited.connect(self._schedule_filter_update)
                self.filter_modell.currentIndexChanged.connect(self._schedule_filter_update)
                if self.filter_seriennummer.lineEdit():
                        self.filter_seriennummer.lineEdit().returnPressed.connect(self.apply_filters)
                        self.filter_seriennummer.lineEdit().textEdited.connect(self._schedule_filter_update)
                self.filter_seriennummer.currentIndexChanged.connect(self._schedule_filter_update)
                self.filter_anmerkungen.returnPressed.connect(self.apply_filters)
                self.filter_anmerkungen.textChanged.connect(self._schedule_filter_update)
                if self.filter_objekttyp.lineEdit():
                        self.filter_objekttyp.lineEdit().returnPressed.connect(self.apply_filters)
                        self.filter_objekttyp.lineEdit().textEdited.connect(self._schedule_filter_update)
                self.filter_objekttyp.currentIndexChanged.connect(self._schedule_filter_update)
                if self.filter_besitzer.lineEdit():
                        self.filter_besitzer.lineEdit().returnPressed.connect(self.apply_filters)
                        self.filter_besitzer.lineEdit().textEdited.connect(self._schedule_filter_update)
                self.filter_besitzer.currentIndexChanged.connect(self._schedule_filter_update)

                selection_model = self.table.selectionModel()
                if selection_model:
                        selection_model.selectionChanged.connect(self._update_item_action_visibility)

                self._update_item_action_visibility()

        # ---------- Daten laden & Status ----------
        def _load_items(self) -> None:
                self.items = self.repository.list()
                self.custom_manufacturers = self.repository.list_custom_values(CUSTOM_CATEGORY_MANUFACTURER)
                self.custom_models = self.repository.list_custom_values(CUSTOM_CATEGORY_MODEL)
                self.custom_serial_numbers = self.repository.list_custom_values(CUSTOM_CATEGORY_SERIAL)
                self.custom_owners = self.repository.list_custom_values(CUSTOM_CATEGORY_OWNER)
                self.filtered_items = list(self.items)
                self.table_model.set_items(self.filtered_items)
                self._refresh_object_types()
                self._update_object_type_filter()
                self._update_manufacturer_filter()
                self._update_model_filter()
                self._update_serial_filter()
                self._update_owner_combo()
                self.apply_filters()
                self._update_item_action_visibility()

        def _update_status(self) -> None:
                total = len(self.items)
                shown = len(self.filtered_items)
                self.statusBar().showMessage(f"Einträge: {shown} / {total}")
                self._update_summary_labels()

        def _update_summary_labels(self) -> None:
                if not hasattr(self, 'user_count_label') or not hasattr(self, 'lager_count_label'):
                        return
                owners = {
                        (item.aktueller_besitzer or '').strip()
                        for item in self.items
                        if item.aktueller_besitzer
                        and item.aktueller_besitzer.strip()
                        and not is_default_owner(item.aktueller_besitzer)
                }
                custom_owners = getattr(self, 'custom_owners', [])
                owners.update(
                        {
                                owner.strip()
                                for owner in custom_owners
                                if owner
                                and owner.strip()
                                and not is_default_owner(owner)
                        }
                )
                lager_items = {
                        item.id
                        for item in self.items
                        if is_default_owner(item.aktueller_besitzer)
                        and item.id is not None
                }
                self.user_count_label.setText(f"User gesamt: {len(owners)}")
                self.lager_count_label.setText(f"Geräte im Lager: {len(lager_items)}")

        def _update_current_owner_label(self, owner: Optional[str]) -> None:
                if not hasattr(self, 'current_owner_label'):
                        return
                owner_text = (owner or '').strip()
                if not owner_text:
                        owner_text = '–'
                self.current_owner_label.setText(f"Aktueller Besitzer: {owner_text}")

        def _update_item_action_visibility(self) -> None:
                selection_model = self.table.selectionModel()
                has_selection = False
                owner: Optional[str] = None
                if selection_model:
                        selected_rows = selection_model.selectedRows()
                        has_selection = bool(selected_rows)
                        if selected_rows:
                                item = self.table_model.item_at(selected_rows[0].row())
                                owner = item.aktueller_besitzer if item else None

                self.edit_action.setEnabled(has_selection)
                self.delete_action.setEnabled(has_selection)
                self._update_current_owner_label(owner)

        # ---------- Hilfen für Combos ----------
        def _merge_custom_values(self, base: Iterable[str], custom: Iterable[str]) -> List[str]:
                merged = {v.strip() for v in base if v and str(v).strip()}
                merged.update({v.strip() for v in custom if v and str(v).strip()})
                merged.discard('')
                return sorted(merged, key=str.casefold)

        def _refresh_object_types(self) -> None:
                self.object_types = self.settings.load_object_types()

        def _update_owner_combo(self, preferred: Optional[str] = None) -> None:
                if not hasattr(self, 'filter_besitzer'):
                        return
                owners = self.repository.distinct_owners() if hasattr(self.repository, 'distinct_owners') else []
                owners = ensure_default_owner(self._merge_custom_values(owners, self.custom_owners))
                target = (preferred or '').strip()
                if not target and self.filter_besitzer.count():
                        target = self.filter_besitzer.currentText().strip()

                self.filter_besitzer.blockSignals(True)
                self.filter_besitzer.clear()
                self.filter_besitzer.addItem('')
                self.filter_besitzer.addItems(owners)
                self.filter_besitzer.blockSignals(False)

                if target:
                        index = self.filter_besitzer.findText(target, Qt.MatchFixedString)
                        if index < 0:
                                lowered = target.lower()
                                for idx in range(1, self.filter_besitzer.count()):
                                        if self.filter_besitzer.itemText(idx).strip().lower() == lowered:
                                                index = idx
                                                break
                        if index >= 0:
                                self.filter_besitzer.setCurrentIndex(index)
                        else:
                                self.filter_besitzer.setCurrentIndex(0)
                                self.filter_besitzer.setEditText('')
                else:
                        self.filter_besitzer.setCurrentIndex(0)
                        self.filter_besitzer.setEditText('')

        def _update_manufacturer_filter(self) -> None:
                if not hasattr(self, 'filter_hersteller'):
                        return
                manufacturers = self.repository.distinct_manufacturers() if hasattr(self.repository, 'distinct_manufacturers') else []
                manufacturers = self._merge_custom_values(manufacturers, self.custom_manufacturers)
                current_text = self.filter_hersteller.currentText().strip() if self.filter_hersteller.count() else ''
                self.filter_hersteller.blockSignals(True)
                self.filter_hersteller.clear()
                self.filter_hersteller.addItem('')
                self.filter_hersteller.addItems(manufacturers)
                if current_text:
                        self.filter_hersteller.setCurrentText(current_text)
                else:
                        self.filter_hersteller.setCurrentIndex(0)
                self.filter_hersteller.blockSignals(False)

        def _update_model_filter(self) -> None:
                if not hasattr(self, 'filter_modell'):
                        return
                models = self.repository.distinct_models() if hasattr(self.repository, 'distinct_models') else []
                models = self._merge_custom_values(models, self.custom_models)
                current_text = self.filter_modell.currentText().strip() if self.filter_modell.count() else ''
                self.filter_modell.blockSignals(True)
                self.filter_modell.clear()
                self.filter_modell.addItem('')
                self.filter_modell.addItems(models)
                if current_text:
                        self.filter_modell.setCurrentText(current_text)
                else:
                        self.filter_modell.setCurrentIndex(0)
                self.filter_modell.blockSignals(False)

        def _update_serial_filter(self) -> None:
                if not hasattr(self, 'filter_seriennummer'):
                        return
                serials = self.repository.distinct_serial_numbers() if hasattr(self.repository, 'distinct_serial_numbers') else []
                serials = self._merge_custom_values(serials, self.custom_serial_numbers)
                current_text = self.filter_seriennummer.currentText().strip() if self.filter_seriennummer.count() else ''
                self.filter_seriennummer.blockSignals(True)
                self.filter_seriennummer.clear()
                self.filter_seriennummer.addItem('')
                self.filter_seriennummer.addItems(serials)
                if current_text:
                        self.filter_seriennummer.setCurrentText(current_text)
                else:
                        self.filter_seriennummer.setCurrentIndex(0)
                self.filter_seriennummer.blockSignals(False)

        def _update_object_type_filter(self) -> None:
                if not hasattr(self, 'filter_objekttyp'):
                        return
                self._refresh_object_types()
                types_list = [t for t in self.object_types if t and str(t).strip()]
                current_text = self.filter_objekttyp.currentText().strip() if self.filter_objekttyp.count() else ''
                self.filter_objekttyp.blockSignals(True)
                self.filter_objekttyp.clear()
                self.filter_objekttyp.addItem('')
                self.filter_objekttyp.addItems(sorted(types_list, key=str.casefold))
                if current_text:
                        self.filter_objekttyp.setCurrentText(current_text)
                else:
                        self.filter_objekttyp.setCurrentIndex(0)
                self.filter_objekttyp.blockSignals(False)

        def _collect_item_dialog_values(self) -> tuple[list[str], list[str], list[str], list[str]]:
                repo_object_types = []
                if hasattr(self.repository, 'distinct_object_types'):
                        repo_object_types = self.repository.distinct_object_types()
                self._refresh_object_types()
                object_types = self._merge_custom_values(repo_object_types, self.object_types)

                repo_manufacturers = []
                if hasattr(self.repository, 'distinct_manufacturers'):
                        repo_manufacturers = self.repository.distinct_manufacturers()
                manufacturers = self._merge_custom_values(repo_manufacturers, self.custom_manufacturers)

                repo_models = []
                if hasattr(self.repository, 'distinct_models'):
                        repo_models = self.repository.distinct_models()
                models = self._merge_custom_values(repo_models, self.custom_models)

                repo_owners = []
                if hasattr(self.repository, 'distinct_owners'):
                        repo_owners = self.repository.distinct_owners()
                owners = ensure_default_owner(self._merge_custom_values(repo_owners, self.custom_owners))

                return object_types, manufacturers, models, owners

        # ---------- Filter/ Suche ----------
        def _handle_search_submit(self) -> None:
                self.apply_filters()

        def _handle_search_text_change(self, text: str) -> None:
                self._schedule_filter_update()

        def _handle_toggle_stillgelegt(self, show_inactive_only: bool) -> None:
                self._update_stillgelegt_toggle_label(show_inactive_only)
                self.apply_filters()

        def _schedule_filter_update(self, *_args) -> None:
                if hasattr(self, '_filter_timer') and self._filter_timer:
                        self._filter_timer.stop()
                        self._filter_timer.start()

        def _update_stillgelegt_toggle_label(self, show_inactive_only: bool) -> None:
                if show_inactive_only:
                        self.toggle_stillgelegt_button.setText('Nur stillgelegte anzeigen')
                        self.toggle_stillgelegt_button.setToolTip('Es werden ausschließlich stillgelegte Einträge angezeigt')
                else:
                        self.toggle_stillgelegt_button.setText('Nur aktive anzeigen')
                        self.toggle_stillgelegt_button.setToolTip('Es werden ausschließlich aktive (nicht stillgelegte) Einträge angezeigt')

        def eventFilter(self, obj, event):  # type: ignore[override]
                return super().eventFilter(obj, event)

        def apply_filters(self) -> None:
                q = self.search_field.text().strip().lower()
                f_type = self.filter_objekttyp.currentText().strip().lower()
                f_man = self.filter_hersteller.currentText().strip().lower()
                f_model = self.filter_modell.currentText().strip().lower()
                f_serial = self.filter_seriennummer.currentText().strip().lower()
                f_owner = self.filter_besitzer.currentText().strip().lower()
                f_notes = self.filter_anmerkungen.text().strip().lower()

                def match_text(val: Optional[str], needle: str) -> bool:
                        if not needle:
                                return True
                        return (val or '').strip().lower().find(needle) != -1

                filtered: List[Item] = []
                for it in self.items:
                        if f_type and (it.objekttyp or '').strip().lower() != f_type:
                                continue
                        if f_man and (it.hersteller or '').strip().lower() != f_man:
                                continue
                        if f_model and (it.modell or '').strip().lower() != f_model:
                                continue
                        if f_serial and (it.seriennummer or '').strip().lower() != f_serial:
                                continue
                        if f_owner and (it.aktueller_besitzer or '').strip().lower() != f_owner:
                                continue
                        if f_notes and not match_text(it.anmerkungen, f_notes):
                                continue
                        if self.toggle_stillgelegt_button.isChecked():
                                if not getattr(it, 'stillgelegt', False):
                                        continue
                        else:
                                if getattr(it, 'stillgelegt', False):
                                        continue
                        if q:
                                haystack = ' '.join([
                                        it.objekttyp or '', it.hersteller or '', it.modell or '', it.seriennummer or '',
                                        it.einkaufsdatum or '', it.zuweisungsdatum or '', it.aktueller_besitzer or '',
                                        it.anmerkungen or ''
                                ]).lower()
                                if q not in haystack:
                                        continue
                        filtered.append(it)

                self.filtered_items = filtered
                self.table_model.set_items(self.filtered_items)
                self._update_status()

        def reset_filters(self) -> None:
                self.search_field.clear()
                for combo in (self.filter_objekttyp, self.filter_hersteller, self.filter_modell, self.filter_seriennummer, self.filter_besitzer):
                        combo.setCurrentIndex(0)
                        combo.setEditText('')
                self.filter_anmerkungen.clear()
                self.toggle_stillgelegt_button.blockSignals(True)
                self.toggle_stillgelegt_button.setChecked(False)
                self.toggle_stillgelegt_button.blockSignals(False)
                self._update_stillgelegt_toggle_label(False)
                self.apply_filters()

        # ---------- Zoom/Font ----------
        def _adjust_font_size(self, delta: int) -> None:
                self._font_size = max(7, min(24, self._font_size + delta))
                f = QFont()
                f.setPointSize(self._font_size)
                self.table.setFont(f)
                self.table.resizeRowsToContents()
                self.table.resizeColumnsToContents()
                try:
                        if hasattr(self.settings, 'save_table'):
                                self.settings.save_table(self.table, self._font_size)
                except Exception:
                        pass

        # ---------- CRUD ----------
        def _current_row_index(self) -> Optional[int]:
                sel = self.table.selectionModel()
                if not sel:
                        return None
                rows = sel.selectedRows()
                if not rows:
                        return None
                return rows[0].row()

        def _selected_item(self) -> Optional[Item]:
                idx = self._current_row_index()
                if idx is None:
                        return None
                return self.table_model.item_at(idx)

        def create_item(self) -> None:
                object_types, manufacturers, models, owners = self._collect_item_dialog_values()
                dialog = ItemDialog(
                        self,
                        item=None,
                        owners=owners,
                        object_types=object_types,
                        manufacturers=manufacturers,
                        models=models,
                )
                result = dialog.exec()
                if result and dialog.result_action == ItemDialog.ACTION_SAVE:
                        new_item = dialog.get_item()
                        try:
                                if hasattr(self.repository, 'create'):
                                        self.repository.create(new_item)
                                else:
                                        self.repository.add(new_item)
                        except RepositoryError as e:
                                QMessageBox.critical(self, 'Fehler', f'Konnte Eintrag nicht speichern:\n{e}')
                                return
                        self._load_items()
                        self.reset_filters()

        def edit_selected_item(self) -> None:
                item = self._selected_item()
                if not item:
                        return
                object_types, manufacturers, models, owners = self._collect_item_dialog_values()
                dialog = ItemDialog(
                        self,
                        item=item,
                        owners=owners,
                        object_types=object_types,
                        manufacturers=manufacturers,
                        models=models,
                )
                result = dialog.exec()
                if dialog.result_action == ItemDialog.ACTION_DELETE:
                        self._delete_item(item)
                        return
                if result and dialog.result_action == ItemDialog.ACTION_SAVE:
                        updated = dialog.get_item()
                        item_id = item.id or updated.id
                        if item_id is None:
                                QMessageBox.critical(self, 'Fehler', 'Aktualisierung fehlgeschlagen:\nObjekt-ID fehlt.')
                                return
                        try:
                                self.repository.update(item_id, updated)
                        except TypeError:
                                # Fallback für Repositories mit älterer Signatur
                                self.repository.update(updated)
                        except AttributeError:
                                # Letzter Fallback falls nur eine add/create-Methode existiert
                                if hasattr(self.repository, 'create'):
                                        self.repository.create(updated)
                                else:
                                        self.repository.add(updated)
                        except RepositoryError as e:
                                QMessageBox.critical(self, 'Fehler', f'Aktualisierung fehlgeschlagen:\n{e}')
                                return
                        self._load_items()
                        self.reset_filters()

        def delete_selected_item(self) -> None:
                item = self._selected_item()
                if not item:
                        return
                self._delete_item(item)

        def _delete_item(self, item: Item) -> None:
                if QMessageBox.question(self, 'Löschen', 'Diesen Eintrag wirklich löschen?') != QMessageBox.Yes:
                        return
                item_id = item.id
                if item_id is None:
                        QMessageBox.critical(self, 'Fehler', 'Löschen fehlgeschlagen:\nObjekt-ID fehlt.')
                        return
                try:
                        self.repository.delete(item_id)
                except TypeError:
                        self.repository.delete(item)
                except RepositoryError as e:
                        QMessageBox.critical(self, 'Fehler', f'Löschen fehlgeschlagen:\n{e}')
                        return
                self._load_items()
                self.apply_filters()

        def _deactivate_item(self, item: Item) -> None:
                item_id = item.id
                if item_id is None:
                        QMessageBox.critical(self, 'Fehler', 'Stilllegen fehlgeschlagen:\nObjekt-ID fehlt.')
                        return
                try:
                        if hasattr(self.repository, 'deactivate'):
                                try:
                                        self.repository.deactivate(item_id)
                                except TypeError:
                                        self.repository.deactivate(item)
                        else:
                                setattr(item, 'stillgelegt', True)
                                try:
                                        self.repository.update(item_id, item)
                                except TypeError:
                                        self.repository.update(item)
                                except AttributeError:
                                        if hasattr(self.repository, 'create'):
                                                self.repository.create(item)
                                        else:
                                                self.repository.add(item)
                except RepositoryError as e:
                        QMessageBox.critical(self, 'Fehler', f'Stilllegen fehlgeschlagen:\n{e}')
                        return
                self._load_items()
                self.apply_filters()

        def deactivate_selected_item(self) -> None:
                item = self._selected_item()
                if not item:
                        return
                self._deactivate_item(item)

        # ---------- Export / Drucken ----------
        def _pick_export_path(self, suffix: str, filter_str: str) -> Optional[Path]:
                fn, _ = QFileDialog.getSaveFileName(self, 'Daten exportieren', f'inventar.{suffix}', filter_str)
                return Path(fn) if fn else None

        def export_data(self, fmt: str) -> None:
                data = self.filtered_items
                try:
                        if fmt == 'xlsx':
                                path = self._pick_export_path('xlsx', 'Excel (*.xlsx)')
                                if not path:
                                        return
                                export_to_xlsx(data, path)
                        elif fmt == 'csv':
                                path = self._pick_export_path('csv', 'CSV (*.csv)')
                                if not path:
                                        return
                                export_to_csv(data, path)
                        elif fmt == 'json':
                                path = self._pick_export_path('json', 'JSON (*.json)')
                                if not path:
                                        return
                                export_to_json(data, path)
                        else:
                                QMessageBox.warning(self, 'Export', f'Unbekanntes Format: {fmt}')
                                return
                except Exception as e:
                        QMessageBox.critical(self, 'Export', f'Export fehlgeschlagen:\n{e}')
                        return
                self.statusBar().showMessage('Export erfolgreich', 4000)

        def import_data_from_file(self) -> None:
                caption = 'Daten importieren'
                filters = 'Excel-Dateien (*.xlsx *.xlsm *.xls);;CSV-Dateien (*.csv);;Alle Dateien (*)'
                selected, _ = QFileDialog.getOpenFileName(self, caption, '', filters)
                if not selected:
                        return
                path = Path(selected)

                try:
                        result = import_items(path)
                except InventoryImportError as exc:
                        QMessageBox.warning(self, 'Import', f'Datei konnte nicht eingelesen werden:\n{exc}')
                        return
                except Exception as exc:  # noqa: BLE001
                        QMessageBox.critical(self, 'Import', f'Unerwarteter Fehler beim Einlesen:\n{exc}')
                        return

                if not result.items:
                        message = 'Es wurden keine gültigen Einträge gefunden.'
                        if result.errors:
                                preview = '\n'.join(result.errors[:10])
                                if len(result.errors) > 10:
                                        preview += f"\n… weitere {len(result.errors) - 10} Meldungen"
                                box = QMessageBox(self)
                                box.setWindowTitle('Import abgeschlossen')
                                box.setIcon(QMessageBox.Warning)
                                box.setText(message)
                                box.setInformativeText('Fehlerdetails:')
                                box.setDetailedText(preview)
                                box.exec()
                        else:
                                QMessageBox.information(self, 'Import', message)
                        return

                created = 0
                storage_errors: list[str] = []
                for idx, item in enumerate(result.items, start=1):
                        try:
                                self.repository.create(item.copy(id=None))
                                created += 1
                        except RepositoryError as exc:
                                storage_errors.append(f'Datensatz {idx}: {exc}')
                        except Exception as exc:  # noqa: BLE001
                                storage_errors.append(f'Datensatz {idx}: {exc}')

                if created:
                        self._load_items()
                summary = f'{created} Einträge importiert.'

                combined_errors = result.errors + storage_errors
                if combined_errors:
                        detail_lines: list[str] = []
                        if result.errors:
                                detail_lines.append('Fehler beim Einlesen:')
                                detail_lines.extend(result.errors)
                        if storage_errors:
                                if detail_lines:
                                        detail_lines.append('')
                                detail_lines.append('Fehler beim Speichern:')
                                detail_lines.extend(storage_errors)
                        preview = '\n'.join(detail_lines[:20])
                        if len(detail_lines) > 20:
                                preview += f"\n… weitere {len(detail_lines) - 20} Meldungen"
                        box = QMessageBox(self)
                        box.setWindowTitle('Import abgeschlossen')
                        box.setIcon(QMessageBox.Warning if created else QMessageBox.Critical)
                        box.setText(summary)
                        box.setInformativeText('Einige Zeilen konnten nicht importiert werden.')
                        box.setDetailedText(preview)
                        box.exec()
                else:
                        QMessageBox.information(self, 'Import', summary)

                self.statusBar().showMessage(summary, 6000)

        def print_items(self) -> None:
                items = list(self.filtered_items)
                if not items:
                        QMessageBox.information(self, 'Drucken', 'Keine Einträge zum Drucken vorhanden.')
                        return

                try:
                        self.printer.print_dialog(items, len(items))
                except Exception as e:
                        QMessageBox.critical(self, 'Drucken', f'Druck fehlgeschlagen:\n{e}')

        # ---------- Objekt-/Eigenschaftswerte pflegen ----------
        def _add_value_via_dialog(self, title: str, label: str) -> Optional[str]:
                text, ok = QInputDialog.getText(self, title, label)
                if ok:
                        text = text.strip()
                        return text or None
                return None

        def _add_owner_filter_value(self) -> None:
                val = self._add_value_via_dialog('Besitzer hinzufügen', 'Name:')
                if not val:
                        return
                if is_default_owner(val):
                        QMessageBox.information(self, 'Besitzer hinzufügen', "Der Eintrag 'LAGER' ist bereits vorhanden.")
                        return
                try:
                        if hasattr(self.repository, 'add_custom_value'):
                                self.repository.add_custom_value(CUSTOM_CATEGORY_OWNER, val)
                        self.custom_owners = self.repository.list_custom_values(CUSTOM_CATEGORY_OWNER)
                except Exception:
                        pass
                self._update_owner_combo(val)
                self._update_summary_labels()

        def _remove_owner_filter_value(self) -> None:
                val = self.filter_besitzer.currentText().strip()
                if not val:
                        return
                if is_default_owner(val):
                        QMessageBox.information(self, 'Besitzer entfernen', "Der Eintrag 'LAGER' kann nicht entfernt werden.")
                        return
                confirm = QMessageBox.question(
                        self,
                        'Besitzer entfernen',
                        (
                                f"Soll der Besitzer '{val}' wirklich aus allen Einträgen entfernt werden?\n"
                                'Diese Aktion kann nicht rückgängig gemacht werden.'
                        ),
                )
                if confirm != QMessageBox.Yes:
                        return

                affected = 0
                try:
                        if hasattr(self.repository, 'clear_owner'):
                                affected = self.repository.clear_owner(val)
                except RepositoryError as exc:
                        QMessageBox.critical(self, 'Besitzer entfernen', f'Besitzer konnte nicht entfernt werden:\n{exc}')
                        return
                except Exception as exc:  # noqa: BLE001
                        QMessageBox.critical(
                                self,
                                'Besitzer entfernen',
                                f'Unerwarteter Fehler beim Entfernen des Besitzers:\n{exc}',
                        )
                        return

                try:
                        if hasattr(self.repository, 'remove_custom_value'):
                                self.repository.remove_custom_value(CUSTOM_CATEGORY_OWNER, val)
                        self.custom_owners = self.repository.list_custom_values(CUSTOM_CATEGORY_OWNER)
                except Exception:
                        pass

                self._load_items()

                message = (
                        f"Besitzer '{val}' wurde in {affected} Einträgen auf '{DEFAULT_OWNER}' gesetzt."
                        if affected
                        else f"Besitzer '{val}' war in keinen Einträgen hinterlegt."
                )
                QMessageBox.information(self, 'Besitzer entfernt', message)


# ---------- Start/Run Helper ----------
def run() -> None:
        app = QApplication.instance() or QApplication([])
        w = MainWindow()
        w.show()
        app.exec()


if __name__ == '__main__':
        run()
