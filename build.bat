cd /d C:\verwaltung_db\verwaltung_db

REM 1) venv aktivieren (optional, aber sauber)
call venv\Scripts\activate

REM 2) Abhängigkeiten + PyInstaller installieren
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
python -m pip install pyinstaller

REM 3) Bauen (eine einzelne EXE)
python -m PyInstaller --noconfirm --clean --onefile --name verwaltung_db ^
  --noconsole ^
  --add-data "assets;assets" ^
  --add-data "inventar.db;." ^
  inventar\app.py
