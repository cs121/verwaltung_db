from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
        QCheckBox,
        QComboBox,
        QDateEdit,
        QDialog,
        QDialogButtonBox,
        QGridLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QPlainTextEdit,
        QPushButton,
        QSizePolicy,
        QVBoxLayout,
        QWidget,
)

from inventar.data.models import Item
from inventar.utils.validators import DATE_FORMAT_QT_DISPLAY, ItemValidator


class ItemDialog(QDialog):
        """Dialog zum Erstellen/Bearbeiten von Items."""

        ACTION_SAVE = 'save'
        ACTION_CANCEL = 'cancel'
        ACTION_DELETE = 'delete'

        def __init__(
                self,
                parent: QWidget | None = None,
                item: Optional[Item] = None,
                owners: Optional[list[str]] = None,
                object_types: Optional[list[str]] = None,
                manufacturers: Optional[list[str]] = None,
                models: Optional[list[str]] = None,
        ) -> None:
                super().__init__(parent)
                self.setWindowTitle('Neues Objekt einfügen' if item is None else 'Objekt bearbeiten')
                self.item = item
                self.owners = owners or []
                self.object_types = object_types or []
                self.manufacturers = manufacturers or []
                self.models = models or []
                self._result_action = ItemDialog.ACTION_CANCEL
                self._stillgelegt_value = bool(item.stillgelegt) if item else False
                self._deactivate_button: QPushButton | None = None
                self._build_ui()
                if item:
                        self._populate(item)
                else:
                        today = QDate.currentDate()
                        self.einkaufsdatum_edit.setDate(today)

        def _build_ui(self) -> None:
                layout = QVBoxLayout(self)

                form_layout = QGridLayout()
                self.objekttyp_combo = QComboBox()
                self.objekttyp_combo.setEditable(True)
                if self.object_types:
                        self.objekttyp_combo.addItems(self.object_types)
                self.hersteller_combo = QComboBox()
                self.hersteller_combo.setEditable(True)
                if self.manufacturers:
                        self.hersteller_combo.addItems(sorted(self.manufacturers))
                self.modell_combo = QComboBox()
                self.modell_combo.setEditable(True)
                if self.models:
                        self.modell_combo.addItems(sorted(self.models))

                for combo in (self.objekttyp_combo, self.hersteller_combo, self.modell_combo):
                        combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

                self.seriennummer_edit = QLineEdit()
                self.einkaufsdatum_edit = QDateEdit()
                # Qt erwartet sein eigenes Datumsformat (dd.MM.yyyy) für die Anzeige.
                # Dieses unterscheidet sich von den strftime-Formaten, die wir für die Validierung nutzen.
                self.einkaufsdatum_edit.setDisplayFormat(DATE_FORMAT_QT_DISPLAY)
                self.einkaufsdatum_edit.setCalendarPopup(True)
                self.zuweisungsdatum_edit = QDateEdit()
                self.zuweisungsdatum_edit.setDisplayFormat(DATE_FORMAT_QT_DISPLAY)
                self.zuweisungsdatum_edit.setCalendarPopup(True)
                self.zuweisungsdatum_edit.setSpecialValueText('')
                self.zuweisungsdatum_edit.setDate(self.zuweisungsdatum_edit.minimumDate())
                self.aktueller_besitzer_combo = QComboBox()
                self.aktueller_besitzer_combo.setEditable(True)
                self.aktueller_besitzer_combo.addItem('')
                if self.owners:
                        for owner in sorted(self.owners):
                                if owner:
                                        self.aktueller_besitzer_combo.addItem(owner)
                self.aktueller_besitzer_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                self.assignment_toggle = QCheckBox()
                self.assignment_toggle.setToolTip('Zuweisung anzeigen/ausblenden')
                owner_container = QWidget()
                owner_layout = QHBoxLayout(owner_container)
                owner_layout.setContentsMargins(0, 0, 0, 0)
                owner_layout.setSpacing(6)
                owner_layout.addWidget(self.aktueller_besitzer_combo)
                owner_layout.addWidget(self.assignment_toggle)
                self.anmerkungen_edit = QPlainTextEdit()
                self.anmerkungen_edit.setStyleSheet('background-color: white;')

                form_layout.addWidget(QLabel('Objekttyp'), 0, 0)
                form_layout.addWidget(self.objekttyp_combo, 0, 1)
                form_layout.addWidget(QLabel('Hersteller'), 1, 0)
                form_layout.addWidget(self.hersteller_combo, 1, 1)
                form_layout.addWidget(QLabel('Modell'), 2, 0)
                form_layout.addWidget(self.modell_combo, 2, 1)

                form_layout.addWidget(QLabel('Seriennummer'), 0, 2)
                form_layout.addWidget(self.seriennummer_edit, 0, 3)
                form_layout.addWidget(QLabel('Einkaufsdatum'), 1, 2)
                form_layout.addWidget(self.einkaufsdatum_edit, 1, 3)
                self.zuweisungsdatum_label = QLabel('Zuweisungsdatum')
                form_layout.addWidget(self.zuweisungsdatum_label, 2, 2)
                form_layout.addWidget(self.zuweisungsdatum_edit, 2, 3)
                self.aktueller_besitzer_label = QLabel('Aktueller Besitzer')
                form_layout.addWidget(self.aktueller_besitzer_label, 3, 0)
                form_layout.addWidget(owner_container, 3, 1, 1, 3)

                layout.addLayout(form_layout)
                layout.addWidget(QLabel('Anmerkungen'))
                layout.addWidget(self.anmerkungen_edit)

                self.button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
                save_button = self.button_box.button(QDialogButtonBox.Save)
                cancel_button = self.button_box.button(QDialogButtonBox.Cancel)
                if save_button:
                        save_button.setText('Speichern')
                if cancel_button:
                        cancel_button.setText('Beenden')
                self.button_box.accepted.connect(self._handle_save_clicked)
                self.button_box.rejected.connect(self._handle_cancel_clicked)
                if self.item is not None:
                        deactivate_button = self.button_box.addButton('Stilllegen', QDialogButtonBox.ActionRole)
                        deactivate_button.setCheckable(True)
                        deactivate_button.setChecked(self._stillgelegt_value)
                        self._deactivate_button = deactivate_button
                        self._update_deactivate_button()
                        deactivate_button.toggled.connect(self._handle_deactivate_toggled)
                        delete_button = self.button_box.addButton('Löschen', QDialogButtonBox.DestructiveRole)
                        delete_button.clicked.connect(self._handle_delete_clicked)
                layout.addWidget(self.button_box)

                self.shortcut_save = QKeySequence(Qt.CTRL | Qt.Key_S)
                self.grabShortcut(self.shortcut_save)
                self.assignment_toggle.toggled.connect(self._handle_assignment_toggled)
                self._handle_assignment_toggled(False)

        def _populate(self, item: Item) -> None:
                if item.objekttyp:
                        index = self.objekttyp_combo.findText(item.objekttyp)
                        if index >= 0:
                                self.objekttyp_combo.setCurrentIndex(index)
                        else:
                                self.objekttyp_combo.setEditText(item.objekttyp)
                if item.hersteller:
                        index = self.hersteller_combo.findText(item.hersteller)
                        if index >= 0:
                                self.hersteller_combo.setCurrentIndex(index)
                        else:
                                self.hersteller_combo.setEditText(item.hersteller)
                else:
                        self.hersteller_combo.setCurrentText('')
                if item.modell:
                        index = self.modell_combo.findText(item.modell)
                        if index >= 0:
                                self.modell_combo.setCurrentIndex(index)
                        else:
                                self.modell_combo.setEditText(item.modell)
                else:
                        self.modell_combo.setCurrentText('')
                self.seriennummer_edit.setText(item.seriennummer)
                if item.einkaufsdatum:
                        qdate = QDate.fromString(item.einkaufsdatum, 'yyyy-MM-dd')
                        if qdate.isValid():
                                self.einkaufsdatum_edit.setDate(qdate)
                if item.zuweisungsdatum:
                        assign_date = QDate.fromString(item.zuweisungsdatum, 'yyyy-MM-dd')
                        if assign_date.isValid():
                                self.zuweisungsdatum_edit.setDate(assign_date)
                else:
                        self.zuweisungsdatum_edit.setDate(self.zuweisungsdatum_edit.minimumDate())
                index = self.aktueller_besitzer_combo.findText(item.aktueller_besitzer)
                if index >= 0:
                        self.aktueller_besitzer_combo.setCurrentIndex(index)
                else:
                        self.aktueller_besitzer_combo.setEditText(item.aktueller_besitzer)
                self.anmerkungen_edit.setPlainText(item.anmerkungen)
                has_assignment = bool(item.aktueller_besitzer or item.zuweisungsdatum)
                self.assignment_toggle.blockSignals(True)
                self.assignment_toggle.setChecked(has_assignment)
                self.assignment_toggle.blockSignals(False)
                self._handle_assignment_toggled(has_assignment)

        def accept(self) -> None:  # type: ignore[override]
                valid, errors = ItemValidator.validate(self._collect_data(display_format=True))
                if not valid:
                        self._show_errors(errors)
                        return
                super().accept()

        def _collect_data(self, display_format: bool = False) -> dict:
                def _date_value(widget: QDateEdit) -> str:
                        text = widget.text().strip()
                        if not text:
                                return ''
                        return text if display_format else widget.date().toString('yyyy-MM-dd')

                return {
                        'objekttyp': self.objekttyp_combo.currentText().strip(),
                        'hersteller': self.hersteller_combo.currentText().strip(),
                        'modell': self.modell_combo.currentText().strip(),
                        'seriennummer': self.seriennummer_edit.text().strip(),
                        'einkaufsdatum': _date_value(self.einkaufsdatum_edit),
                        'zuweisungsdatum': _date_value(self.zuweisungsdatum_edit),
                        'aktueller_besitzer': self.aktueller_besitzer_combo.currentText().strip(),
                        'anmerkungen': self.anmerkungen_edit.toPlainText().strip(),
                        'stillgelegt': self._stillgelegt_value,
                }

        def _show_errors(self, errors: dict) -> None:
                messages = '\n'.join(f"{field}: {message}" for field, message in errors.items())
                from PySide6.QtWidgets import QMessageBox

                QMessageBox.warning(self, 'Eingabe ungültig', messages)

        def get_item_data(self) -> dict:
                return self._collect_data()

        def get_item(self) -> Item:
                data = self._collect_data()
                if self.item:
                        return self.item.copy(**data)
                return Item(**data)

        @property
        def result_action(self) -> str:
                return self._result_action

        def _handle_save_clicked(self) -> None:
                self._result_action = ItemDialog.ACTION_SAVE
                self.accept()

        def _handle_delete_clicked(self) -> None:
                self._result_action = ItemDialog.ACTION_DELETE
                self.done(QDialog.Accepted)

        def _handle_deactivate_toggled(self, checked: bool) -> None:
                self._stillgelegt_value = checked
                if not checked:
                        self._remove_stillgelegt_note()
                self._update_deactivate_button()

        def _handle_assignment_toggled(self, checked: bool) -> None:
                self._set_assignment_fields_visible(checked)
                self._set_assignment_fields_enabled(checked)
                if not checked:
                        self.aktueller_besitzer_combo.setCurrentText('')
                        self.zuweisungsdatum_edit.setDate(self.zuweisungsdatum_edit.minimumDate())

        def _set_assignment_fields_visible(self, visible: bool) -> None:
                for widget in (
                        self.zuweisungsdatum_label,
                        self.zuweisungsdatum_edit,
                        self.aktueller_besitzer_label,
                        self.aktueller_besitzer_combo,
                ):
                        widget.setVisible(visible)

        def _set_assignment_fields_enabled(self, enabled: bool) -> None:
                self.zuweisungsdatum_edit.setEnabled(enabled)
                self.aktueller_besitzer_combo.setEnabled(enabled)

        def _handle_cancel_clicked(self) -> None:
                self._result_action = ItemDialog.ACTION_CANCEL
                self.reject()

        def reject(self) -> None:  # type: ignore[override]
                self._result_action = ItemDialog.ACTION_CANCEL
                super().reject()

        def _update_deactivate_button(self) -> None:
                if not self._deactivate_button:
                        return
                if self._stillgelegt_value:
                        self._deactivate_button.setText('Stilllegen: AN')
                        self._deactivate_button.setStyleSheet('background-color: #c62828; color: white;')
                else:
                        self._deactivate_button.setText('Stilllegen: AUS')
                        self._deactivate_button.setStyleSheet('')

        def _remove_stillgelegt_note(self) -> None:
                text = self.anmerkungen_edit.toPlainText()
                if not text:
                        return
                lines = text.splitlines()
                filtered_lines = [line for line in lines if line.strip().lower() != 'stillgelegt']
                new_text = '\n'.join(filtered_lines).rstrip()
                self.anmerkungen_edit.setPlainText(new_text)
