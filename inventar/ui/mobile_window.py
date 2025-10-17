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
        self._current_index: Optional[int] = None

        self._build_ui()
        self._connect_signals()
        self._populate_owner_fields()
        self._update_table()

    # ---------- Initialisierung ----------
    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)

        form_layout = QHBoxLayout()

        self.main_group = QGroupBox("Hauptkarte")
        main_form = QFormLayout(self.main_group)
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

        self.secondary_group = QGroupBox("Zweitkarte")
        second_form = QFormLayout(self.secondary_group)
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

        form_layout.addWidget(self.main_group)
        form_layout.addWidget(self.secondary_group)

        button_row = QHBoxLayout()
        self.reset_button = QPushButton("Zurücksetzen")
        self.save_button = QPushButton("Speichern")
        self.delete_button = QPushButton("Löschen")
        self.delete_button.setEnabled(False)
        button_row.addWidget(self.reset_button)
        button_row.addWidget(self.save_button)
        button_row.addWidget(self.delete_button)
        button_row.addStretch()

        search_group = QGroupBox("Nummer suchen")
        search_layout = QHBoxLayout(search_group)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Telefon- oder Zweitnummer")
        self.search_button = QPushButton("Suchen")
        search_layout.addWidget(self.search_edit)
        search_layout.addWidget(self.search_button)

        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.setSelectionBehavior(self.table.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(self.table.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)

        main_layout.addLayout(form_layout)
        main_layout.addLayout(button_row)
        main_layout.addWidget(search_group)
        main_layout.addWidget(self.table)

    def _create_owner_combo(self) -> QComboBox:
        combo = QComboBox()
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.NoInsert)
        return combo

    def _connect_signals(self) -> None:
        self.reset_button.clicked.connect(self._reset_form)
        self.save_button.clicked.connect(self._handle_save)
        self.delete_button.clicked.connect(self._handle_delete)
        self.search_button.clicked.connect(self._handle_search)
        self.table.itemSelectionChanged.connect(self._handle_table_selection)

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

    # ---------- Aktionen ----------
    def set_owners(self, owners: List[str]) -> None:
        """Aktualisiert die verfügbaren Besitzer:innen in beiden Auswahlfeldern."""

        self._owners = sorted({owner for owner in owners if owner})
        self._populate_owner_fields()

    def _handle_save(self) -> None:
        entry = self._collect_entry_data()
        if entry is None:
            return
        if self._current_index is None:
            self._entries.append(entry)
        else:
            self._entries[self._current_index] = entry
        self._update_table()
        self._reset_form()

    def _handle_delete(self) -> None:
        if self._current_index is None:
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
        del self._entries[self._current_index]
        self._update_table()
        self._reset_form()

    def _handle_search(self) -> None:
        query = self.search_edit.text().strip().lower()
        if not query:
            return
        for index, entry in enumerate(self._entries):
            if query in entry.telefonnummer.lower() or (
                entry.zweite_telefonnummer and query in entry.zweite_telefonnummer.lower()
            ):
                self.table.selectRow(index)
                self.table.scrollToItem(self.table.item(index, 0))
                return
        QMessageBox.information(self, "Keine Treffer", "Es wurde kein Eintrag gefunden.")

    def _handle_table_selection(self) -> None:
        selected_items = self.table.selectedItems()
        if not selected_items:
            self._current_index = None
            self.delete_button.setEnabled(False)
            return
        row = selected_items[0].row()
        self._current_index = row
        self.delete_button.setEnabled(True)
        entry = self._entries[row]
        self._fill_form(entry)

    # ---------- Hilfsfunktionen ----------
    def _collect_entry_data(self) -> Optional[MobileEntry]:
        telefonnummer = self.phone_main_edit.text().strip()
        if not telefonnummer:
            QMessageBox.warning(self, "Eingabe unvollständig", "Bitte geben Sie mindestens eine Telefonnummer an.")
            return None
        entry = MobileEntry(
            telefonnummer=telefonnummer,
            pin=self.pin_main_edit.text().strip(),
            super_pin=self.super_pin_main_edit.text().strip(),
            zugewiesen_an=self.assign_main_combo.currentText().strip(),
            zweite_telefonnummer=self.phone_second_edit.text().strip(),
            zweite_pin=self.pin_second_edit.text().strip(),
            zweite_super_pin=self.super_pin_second_edit.text().strip(),
            zweite_zugewiesen_an=self.assign_second_combo.currentText().strip(),
        )
        return entry

    def _fill_form(self, entry: MobileEntry) -> None:
        self.phone_main_edit.setText(entry.telefonnummer)
        self.pin_main_edit.setText(entry.pin)
        self.super_pin_main_edit.setText(entry.super_pin)
        self.assign_main_combo.setCurrentText(entry.zugewiesen_an)
        self.phone_second_edit.setText(entry.zweite_telefonnummer)
        self.pin_second_edit.setText(entry.zweite_pin)
        self.super_pin_second_edit.setText(entry.zweite_super_pin)
        self.assign_second_combo.setCurrentText(entry.zweite_zugewiesen_an)

    def _reset_form(self) -> None:
        self._current_index = None
        self.table.clearSelection()
        self.phone_main_edit.clear()
        self.pin_main_edit.clear()
        self.super_pin_main_edit.clear()
        self.assign_main_combo.setCurrentIndex(0)
        self.phone_second_edit.clear()
        self.pin_second_edit.clear()
        self.super_pin_second_edit.clear()
        self.assign_second_combo.setCurrentIndex(0)
        self.search_edit.clear()
        self.delete_button.setEnabled(False)

    def _update_table(self) -> None:
        self.table.setRowCount(len(self._entries))
        for row, entry in enumerate(self._entries):
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

    def entries(self) -> List[MobileEntry]:
        """Gibt eine Kopie der gepflegten Einträge zurück."""

        return list(self._entries)
