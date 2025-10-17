from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


@dataclass
class MobileEntry:
    """Repräsentiert einen Mobilgeräte-Eintrag in der Eingabemaske."""

    telefonnummer: str
    pin: str
    super_pin: str
    zugewiesen_an: str
    zweite_telefonnummer: str
    zweite_pin: str
    zweite_super_pin: str
    zweite_zugewiesen_an: str


class MobileEntryDialog(QDialog):
    """Dialog zur Erfassung oder Bearbeitung eines Mobilgeräte-Eintrags."""

    def __init__(self, owners: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Mobilgerät")
        self._owners = sorted({owner for owner in owners if owner})
        self._entry: Optional[MobileEntry] = None
        self._delete_requested = False

        self._build_ui()
        self._populate_owner_fields()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        form_layout = QHBoxLayout()

        main_group = QGroupBox("Hauptkarte")
        main_form = QFormLayout(main_group)
        self.phone_main_edit = QLineEdit()
        self.phone_main_edit.setPlaceholderText("Telefonnummer eingeben")
        self.pin_main_edit = QLineEdit()
        self.pin_main_edit.setPlaceholderText("PIN eingeben")
        self.super_pin_main_edit = QLineEdit()
        self.super_pin_main_edit.setPlaceholderText("Super-PIN eingeben")
        self.assign_main_combo = self._create_owner_combo()

        main_form.addRow(QLabel("Telefonnummer"), self.phone_main_edit)
        main_form.addRow(QLabel("PIN"), self.pin_main_edit)
        main_form.addRow(QLabel("Super-PIN"), self.super_pin_main_edit)
        main_form.addRow(QLabel("Zugewiesen an"), self.assign_main_combo)

        secondary_group = QGroupBox("Zweitkarte")
        second_form = QFormLayout(secondary_group)
        self.phone_second_edit = QLineEdit()
        self.phone_second_edit.setPlaceholderText("Zweitkarte-Nummer eingeben")
        self.pin_second_edit = QLineEdit()
        self.pin_second_edit.setPlaceholderText("PIN der Zweitkarte eingeben")
        self.super_pin_second_edit = QLineEdit()
        self.super_pin_second_edit.setPlaceholderText("Super-PIN der Zweitkarte eingeben")
        self.assign_second_combo = self._create_owner_combo()

        second_form.addRow(QLabel("Telefonnummer"), self.phone_second_edit)
        second_form.addRow(QLabel("PIN"), self.pin_second_edit)
        second_form.addRow(QLabel("Super-PIN"), self.super_pin_second_edit)
        second_form.addRow(QLabel("Zugewiesen an"), self.assign_second_combo)

        form_layout.addWidget(main_group)
        form_layout.addWidget(secondary_group)
        layout.addLayout(form_layout)

        button_row = QHBoxLayout()
        self.save_button = QPushButton("Speichern")
        self.delete_button = QPushButton("Löschen")
        self.cancel_button = QPushButton("Abbrechen")
        button_row.addStretch()
        button_row.addWidget(self.delete_button)
        button_row.addWidget(self.save_button)
        button_row.addWidget(self.cancel_button)
        layout.addLayout(button_row)

        self.save_button.clicked.connect(self._handle_save)
        self.delete_button.clicked.connect(self._handle_delete)
        self.cancel_button.clicked.connect(self.reject)

        self._update_delete_state(False)

    def _create_owner_combo(self) -> QComboBox:
        combo = QComboBox()
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.NoInsert)
        return combo

    def _populate_owner_fields(self) -> None:
        for combo in (self.assign_main_combo, self.assign_second_combo):
            current = combo.currentText()
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("")
            for owner in self._owners:
                combo.addItem(owner)
            combo.setCurrentText(current)
            combo.blockSignals(False)

    def set_owners(self, owners: list[str]) -> None:
        self._owners = sorted({owner for owner in owners if owner})
        self._populate_owner_fields()

    def set_entry(self, entry: MobileEntry) -> None:
        self._entry = entry
        self.phone_main_edit.setText(entry.telefonnummer)
        self.pin_main_edit.setText(entry.pin)
        self.super_pin_main_edit.setText(entry.super_pin)
        self.assign_main_combo.setCurrentText(entry.zugewiesen_an)
        self.phone_second_edit.setText(entry.zweite_telefonnummer)
        self.pin_second_edit.setText(entry.zweite_pin)
        self.super_pin_second_edit.setText(entry.zweite_super_pin)
        self.assign_second_combo.setCurrentText(entry.zweite_zugewiesen_an)
        self._delete_requested = False
        self._update_delete_state(True)

    def entry(self) -> Optional[MobileEntry]:
        return self._entry

    def delete_requested(self) -> bool:
        return self._delete_requested

    def _handle_save(self) -> None:
        telefonnummer = self.phone_main_edit.text().strip()
        if not telefonnummer:
            QMessageBox.warning(
                self,
                "Eingabe unvollständig",
                "Bitte geben Sie mindestens eine Telefonnummer an.",
            )
            return

        self._entry = MobileEntry(
            telefonnummer=telefonnummer,
            pin=self.pin_main_edit.text().strip(),
            super_pin=self.super_pin_main_edit.text().strip(),
            zugewiesen_an=self.assign_main_combo.currentText().strip(),
            zweite_telefonnummer=self.phone_second_edit.text().strip(),
            zweite_pin=self.pin_second_edit.text().strip(),
            zweite_super_pin=self.super_pin_second_edit.text().strip(),
            zweite_zugewiesen_an=self.assign_second_combo.currentText().strip(),
        )
        self._delete_requested = False
        self.accept()

    def _handle_delete(self) -> None:
        if not self._entry:
            return
        reply = QMessageBox.question(
            self,
            "Eintrag löschen",
            "Möchten Sie den ausgewählten Eintrag wirklich löschen?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self._delete_requested = True
        self.accept()

    def _update_delete_state(self, enabled: bool) -> None:
        self.delete_button.setEnabled(enabled)


class MobileWindow(QDialog):
    """Nicht-modales Fenster zur Pflege von Mobilgeräten."""

    COLUMNS = [
        "Telefonnummer",
        "PIN",
        "Super-PIN",
        "Zugewiesen an",
        "Telefonnummer (Zweitkarte)",
        "PIN (Zweitkarte)",
        "Super-PIN (Zweitkarte)",
        "Zugewiesen an (Zweitkarte)",
    ]

    def __init__(self, owners: Optional[List[str]] = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Mobilgeräte verwalten")
        self.resize(900, 600)
        self.setWindowModality(Qt.NonModal)

        self._owners: list[str] = sorted(owners or [])
        self._entries: list[MobileEntry] = []
        self._visible_indices: list[int] = []

        self._build_ui()
        self._connect_signals()
        self._update_table()

    # ---------- Initialisierung ----------
    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)

        search_group = QGroupBox("Nummer suchen")
        search_layout = QHBoxLayout(search_group)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Telefon- oder Zweitnummer")
        self.search_button = QPushButton("Suchen")
        search_layout.addWidget(self.search_edit)
        search_layout.addWidget(self.search_button)
        main_layout.addWidget(search_group)

        button_row = QHBoxLayout()
        self.new_entry_button = QPushButton("Neues Objekt")
        button_row.addWidget(self.new_entry_button)
        button_row.addStretch()
        main_layout.addLayout(button_row)

        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.setSelectionBehavior(self.table.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(self.table.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        main_layout.addWidget(self.table)

    def _connect_signals(self) -> None:
        self.new_entry_button.clicked.connect(self._open_new_entry_dialog)
        self.search_button.clicked.connect(self._apply_search_filter)
        self.search_edit.textChanged.connect(self._apply_search_filter)
        self.table.itemDoubleClicked.connect(self._handle_table_double_click)

    # ---------- Aktionen ----------
    def set_owners(self, owners: List[str]) -> None:
        """Aktualisiert die verfügbaren Besitzer:innen für neue Dialoge."""

        self._owners = sorted({owner for owner in owners if owner})

    def _apply_search_filter(self) -> None:
        query = self.search_edit.text().strip().lower()
        if not query:
            self._update_table()
            return

        matching_indices: list[int] = []
        for index, entry in enumerate(self._entries):
            fields = [
                entry.telefonnummer,
                entry.pin,
                entry.super_pin,
                entry.zugewiesen_an,
                entry.zweite_telefonnummer,
                entry.zweite_pin,
                entry.zweite_super_pin,
                entry.zweite_zugewiesen_an,
            ]
            for field in fields:
                if field and query in field.lower():
                    matching_indices.append(index)
                    break

        self._update_table(matching_indices)

    def _open_new_entry_dialog(self) -> None:
        self._open_entry_dialog()

    def _open_entry_dialog(self, index: Optional[int] = None) -> None:
        dialog = MobileEntryDialog(self._owners, self)
        if index is not None:
            dialog.set_entry(self._entries[index])
        if dialog.exec() != QDialog.Accepted:
            return

        if dialog.delete_requested():
            if index is None:
                return
            del self._entries[index]
        else:
            entry = dialog.entry()
            if entry is None:
                return
            if index is None:
                self._entries.append(entry)
            else:
                self._entries[index] = entry

        self._update_table()

    def _handle_table_double_click(self, item: QTableWidgetItem) -> None:
        row = item.row()
        if row >= len(self._visible_indices):
            return
        entry_index = self._visible_indices[row]
        self._open_entry_dialog(entry_index)

    # ---------- Hilfsfunktionen ----------
    def _update_table(self, indices: Optional[List[int]] = None) -> None:
        if indices is None:
            indices = list(range(len(self._entries)))

        self._visible_indices = indices
        self.table.setRowCount(len(indices))
        for row, entry_index in enumerate(indices):
            entry = self._entries[entry_index]
            values = [
                entry.telefonnummer,
                entry.pin,
                entry.super_pin,
                entry.zugewiesen_an,
                entry.zweite_telefonnummer,
                entry.zweite_pin,
                entry.zweite_super_pin,
                entry.zweite_zugewiesen_an,
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, column, item)

        self.table.clearSelection()

    def entries(self) -> List[MobileEntry]:
        """Gibt eine Kopie der gepflegten Einträge zurück."""

        return list(self._entries)
