from datetime import datetime
from typing import Iterable

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
from PySide6.QtPrintSupport import QPrintDialog, QPrinter, QPrintPreviewDialog
from PySide6.QtWidgets import QMessageBox, QWidget

from inventar.data.models import Item
from inventar.utils.validators import ItemValidator

HEADER = [
        'Objekttyp',
        'Hersteller',
        'Modell',
        'Seriennummer',
        'Einkaufsdatum',
        'Zuweisungsdatum',
        'Aktueller Besitzer',
        'Anmerkungen',
]


class TablePrinter:
        """Kapselt Drucklogik für die Tabelle."""

        def __init__(self, parent: QWidget) -> None:
                self.parent = parent

        def _create_printer(self) -> QPrinter:
                printer = QPrinter(QPrinter.HighResolution)
                printer.setPageOrientation(Qt.PortraitOrientation)
                printer.setFullPage(False)
                printer.setDocName('Inventarliste')
                return printer

        def preview(self, items: Iterable[Item], total: int) -> None:
                printer = self._create_printer()
                preview = QPrintPreviewDialog(printer, self.parent)
                preview.setWindowTitle('Druckvorschau')
                preview.paintRequested.connect(lambda p: self._render(p, items, total))
                preview.exec()

        def print_dialog(self, items: Iterable[Item], total: int) -> None:
                printer = self._create_printer()
                dialog = QPrintDialog(printer, self.parent)
                if dialog.exec() == QPrintDialog.Accepted:
                        self._render(printer, items, total)

        def export_pdf(self, items: Iterable[Item], total: int, path: str) -> None:
                printer = QPrinter(QPrinter.HighResolution)
                printer.setOutputFormat(QPrinter.PdfFormat)
                printer.setOutputFileName(path)
                self._render(printer, items, total)

        def _render(self, printer: QPrinter, items: Iterable[Item], total: int) -> None:
                painter = QPainter()
                if not painter.begin(printer):
                        QMessageBox.warning(self.parent, 'Druck', 'Konnte Druck nicht starten.')
                        return

                try:
                        self._render_content(painter, printer, list(items), total)
                finally:
                        painter.end()

        def _render_content(self, painter: QPainter, printer: QPrinter, items: list[Item], total: int) -> None:
                rect = printer.pageRect()
                margin = 20
                x = rect.left() + margin
                y = rect.top() + margin
                line_height = 24

                header_text = f"Inventarliste – {datetime.now().strftime('%d.%m.%Y %H:%M')} – Gesamt: {total}"
                painter.drawText(x, y, header_text)
                y += line_height * 2

                column_width = rect.width() // len(HEADER)
                for index, title in enumerate(HEADER):
                        painter.drawText(x + index * column_width, y, title)
                y += line_height

                for item in items:
                        einkaufsdatum = ItemValidator.convert_iso_to_display(item.einkaufsdatum)
                        zuweisungsdatum = ItemValidator.convert_iso_to_display(item.zuweisungsdatum)
                        values = [
                                item.objekttyp,
                                item.hersteller,
                                item.modell,
                                item.seriennummer,
                                einkaufsdatum,
                                zuweisungsdatum,
                                item.aktueller_besitzer,
                                item.anmerkungen,
                        ]

                        if y > rect.bottom() - margin:
                                printer.newPage()
                                y = rect.top() + margin

                        for index, value in enumerate(values):
                                painter.drawText(x + index * column_width, y, str(value))
                        y += line_height
