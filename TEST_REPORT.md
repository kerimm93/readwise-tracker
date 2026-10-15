# Testbericht · Phase 1 · f_n7v28ze4

Stand: 15.10.2026. Ausgeführt in Chromium über Python Playwright mit isoliertem
Browserprofil und temporärem lokalem HTTP-Server. Kein persönlicher Token verwendet.

## Ergebnis

`python3 tests/triage_browser.py`: **52 Prüfungen erfolgreich**, keine fehlgeschlagenen
Prüfungen und keine unbehandelten JavaScript-Ausnahmen. Die Testdatei enthält die
einzelnen Assertions und gibt jede erfolgreich geprüfte Bedingung aus.

Geprüft wurden:

- fünf Inhalte nacheinander bewerten; Interesse 0–5, mehrere aktive Routen,
  exklusive Routen und unabhängige Reader-Aktionsabsicht;
- wortgetreue Notizen, Entwürfe, aktuelle Karte und Entscheidungen nach Reload;
- Zurück, spätere Entscheidung, letzte Entscheidung bearbeiten, Revisionserhöhung
  bei Änderungen und keine künstliche Revision bei identischem Speichern;
- stabile IDs, identische Syncs ohne neue Karten, erneutes Öffnen, Fortschrittsänderung,
  frühere Dokumententscheidung sichtbar und ausschließlich bewusst übernehmbar;
- nachträglicher älterer Backfill ohne Verlust und ohne erfundenes Öffnungsdatum;
- echter JSON-Dateiexport, Importvorschau und bestätigter Restore einschließlich
  Revisionshistorie, Queue und Navigation; Token bleibt im Browser;
- alte Backups ohne Triage, ungültige Routen, Queue-Referenzen und zukünftige
  State-Versionen; fehlerhafter persistierter State bleibt unberührt;
- Wiederherstellung eines gültigen Backups nach fehlgeschlagener Startmigration;
- abgebrochene IndexedDB-Transaktion nach erfolgreichem `put`-Request: kein
  Kartenwechsel; erneutes Speichern nach Wiederherstellung funktioniert;
- Kalender, Timeline, Bibliothek, Triage, Kategorie-Filter und gespeichertes E-Ink-Design;
- aktualisierter Service-Worker-Cache und tatsächliches Neuladen bei Offline-Netzwerk;
- ursprünglicher 31-Tage-Erstsync, alle sieben Kategorien, mehrseitiger Abruf,
  inkrementelles `updatedAfter`, kontrollierter Lazy-History-Abruf und Cursor;
- HTTP 429 mit Retry-After und erneutem Request; API-Fehler verändern weder
  erfolgreichen Sync-Zeitpunkt noch History-Cursor;
- Triage erzeugt keine externen Requests, alle simulierten Reader-Requests sind GET.

Zusätzlich: JavaScript-Syntax mit `node --check`, `git diff --check` und mobile
Darstellung bei 390 px Breite geprüft. Kein horizontaler Seitenüberlauf.

## Grenzen

Reader-Netzwerkantworten sind simuliert. Wartezeiten der API-Tests werden gezielt
verkürzt; Header-Verarbeitung und Abrufkontrolle werden ausgeführt. Echte Reader-
Authentifizierung, Live-API-Verhalten, große persönliche Bibliotheken und physische
Mobilgeräte wurden nicht geprüft. Das Backup ist weiterhin ein bestätigter kompletter
Restore und kein automatischer Geräteabgleich.

Notion-Coding-Log: wegen fehlender Verbindung nicht geschrieben oder verifiziert;
lokaler Ersatznachweis in `CODING_LOG.md`. Phase-2-Funktionen wurden nicht implementiert.
