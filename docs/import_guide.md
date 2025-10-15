# Import von Inventardaten

Dieses Dokument beschreibt, wie Daten aus Excel- oder CSV-Dateien in die Inventarverwaltung übernommen werden können.

## Datei vorbereiten

1. Öffnen Sie am besten zunächst einen bestehenden Export aus der Anwendung (Excel/CSV) und verwenden Sie ihn als Vorlage.
2. Zulässige Dateiformate:
   - Excel: `.xlsx`, `.xlsm`, `.xls`
   - CSV: `.csv` (UTF-8-codiert empfohlen)
3. Folgende Spalten werden erkannt (Groß-/Kleinschreibung ist egal, Leerzeichen oder Bindestriche sind erlaubt):
   - `Objekttyp` *(Pflichtfeld)*
   - `Hersteller`
   - `Modell`
   - `Seriennummer`
   - `Einkaufsdatum`
   - `Zuweisungsdatum`
   - `Aktueller Besitzer`
   - `Anmerkungen`
   - Optional: `Stillgelegt` (Ja/Nein bzw. 1/0)
4. Datumswerte dürfen im Format `TT.MM.JJJJ`, `TT.MM.JJ` oder `JJJJ-MM-TT` vorliegen. Excel-Seriendaten werden automatisch erkannt.
5. Leere Zeilen oder Datensätze ohne sinnvolle Inhalte werden beim Import ignoriert.

## Import durchführen

1. Starten Sie die Anwendung und öffnen Sie die Inventarliste.
2. Klicken Sie unten links auf **Importieren …** oder verwenden Sie im Menü **Datei → Daten importieren …** (Tastenkürzel `Ctrl+I`).
3. Wählen Sie die vorbereitete Excel- oder CSV-Datei aus und bestätigen Sie den Dialog.
4. Nach dem Einlesen zeigt die Anwendung eine Zusammenfassung an:
   - Anzahl der neu angelegten Einträge.
   - Falls es Probleme gab, erscheinen die ersten Fehlermeldungen als Detailansicht (z. B. ungültige Daten oder Schreibfehler).
5. Erfolgreich importierte Datensätze werden sofort in der Liste angezeigt und können wie gewohnt gefiltert oder bearbeitet werden.

## Typische Fehlermeldungen

- **„Erforderliche Spalte fehlt“** – die Spalte `Objekttyp` wurde nicht gefunden. Prüfen Sie die Überschriften.
- **„Ungültiges Datum“** – Datumsangaben konnten nicht interpretiert werden. Korrigieren Sie das Format.
- **„Ungültiger Wahrheitswert für 'stillgelegt'“** – nur `ja/nein`, `true/false`, `1/0` (oder leer) sind erlaubt.
- **Fehler beim Speichern** – der Datensatz konnte nicht in die Datenbank geschrieben werden (z. B. wegen einer beschädigten Datei). Details finden Sie in der Meldung.

> Tipp: Wenn Sie sich unsicher sind, erstellen Sie zunächst einen Export, passen Sie die Daten an und importieren Sie die Datei anschließend wieder.
