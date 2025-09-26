from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from inventar.ui.main_window import run


def main() -> None:
	app = QApplication.instance() or QApplication(sys.argv)
	run()


if __name__ == '__main__':
	main()
