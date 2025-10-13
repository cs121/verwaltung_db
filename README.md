# Inventarliste

Eine plattformunabhängige Desktop-Anwendung zur Verwaltung von Hardware- und sonstigen Inventargegenständen auf Basis von PySide6 und SQLite. Das Programm bietet komfortable Such- und Filtermöglichkeiten, Exportfunktionen sowie eine Druckvorschau und speichert persönliche Einstellungen der Anwender:innen.

## Voraussetzungen

- Python 3.9 oder neuer
- Betriebssystem mit grafischer Oberfläche (getestet unter Windows 10/11 und Linux)
- Optional: Für den Windows-Build wird zusätzlich [PyInstaller](https://pyinstaller.org) benötigt.

Die benötigten Python-Abhängigkeiten sind in `requirements.txt` aufgeführt und werden während der Installation automatisch eingespielt.

## Installation & Start

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python -m inventar
```

Beim ersten Start wird im Projektverzeichnis automatisch die Datenbank `inventar.db` angelegt. Sollte SQLite nicht verfügbar sein, erfolgt ein automatischer Fallback auf die JSON-Datei `inventar_fallback.json`.

## Zentrale Funktionen

- Vollständiges CRUD für Inventargegenstände inklusive Stilllegen-Option
- Pflege eines Objekttyp-Katalogs mit frei erweiterbaren Auswahlwerten
- Live-Suche und kombinierbare Filter (z. B. nach Hersteller, Modell, Besitzer)
- Zusätzliche Datumsfelder für Einkauf und Zuweisung mit Validierung und automatischer ISO-Formatierung
- Export in Excel (XLSX), CSV und JSON sowie Druckvorschau mit PDF-Ausgabe
- Speicherung der Fenster-, Tabellen- und Schriftgrößeneinstellungen via QSettings
- Automatisches Ergänzen eines Hinweistextes für stillgelegte Geräte

## Datenhaltung & Einstellungen

- **Primäre Datenbank:** `inventar.db` im Projekt- bzw. Arbeitsverzeichnis. Die Tabelle `items` enthält alle Inventareinträge, ergänzende Werte werden in `custom_values` gespeichert.
- **Fallback:** Scheitert das Initialisieren der SQLite-Datenbank, nutzt die Anwendung ein JSON-Repository (`inventar_fallback.json`) mit identischem Datenmodell.
- **Benutzereinstellungen:** Fenstergrößen, Tabellenlayout, Schriftgrößen und benutzerdefinierte Objekttypen werden per QSettings abgelegt und beim nächsten Start wiederhergestellt.

## Export und Druck

Über das Menü lassen sich Inventarlisten als Excel-, CSV- oder JSON-Datei exportieren. Zusätzlich steht eine Druckvorschau mit PDF-Export zur Verfügung, sodass Listen direkt weitergegeben oder archiviert werden können.

## Projektstruktur

```
verwaltung_db/
├─ assets/            # Anwendungssymbole
├─ inventar/          # Quellcode der Anwendung
│  ├─ data/           # Datenmodelle und Repository-Implementierungen
│  ├─ export/         # Export-Funktionen (CSV, XLSX, JSON)
│  ├─ ui/             # Qt-Dialoge, Hauptfenster, Druckansicht
│  └─ utils/          # Einstellungen und Validierungen
├─ inventar.db        # SQLite-Datenbank (wird automatisch erstellt)
├─ build.bat          # PyInstaller-Buildskript für Windows
└─ requirements.txt   # Python-Abhängigkeiten
```

## Entwicklung & Tests

- Für lokale Entwicklung empfiehlt sich der Start über `python -m inventar`, da die Qt-Ereignisschleife korrekt initialisiert wird.
- Die Business-Logik ist bewusst in Repository-, Export- und UI-Module getrennt, sodass Funktionserweiterungen klar abgegrenzt werden können.
- Aktuell existiert keine automatisierte Testsuite; Änderungen sollten daher manuell in der Oberfläche geprüft werden.

## Windows-Build mit PyInstaller

Das Skript `build.bat` demonstriert den Build-Prozess für eine portable Windows-Exe. Es aktiviert optional eine virtuelle Umgebung, installiert Abhängigkeiten und packt anschließend die Anwendung inklusive Assets und Datenbank in eine Einzeldatei.

## Support & Weiterentwicklung

Für Feature-Wünsche oder Bugmeldungen bitte Issues im zugehörigen Repository anlegen oder Pull-Requests einreichen. Beiträge in Form von Dokumentation, Tests oder neuen Funktionen sind ausdrücklich willkommen.
