# Testbericht · Phase 1 · f_n7v28ze4

Stand: 15.10.2026. Ausgeführt in Chromium über Python Playwright mit isoliertem
Browserprofil und temporärem lokalem HTTP-Server. Kein persönlicher Token verwendet.

## Ergebnis

`python3 tests/triage_browser.py`: **52 Prüfungen erfolgreich**.
`python3 tests/triage_review_browser.py`: **21 weitere Prüfungen erfolgreich**.
Insgesamt **73 erfolgreiche Prüfungen**, keine fehlgeschlagenen Prüfungen und
keine unbehandelten JavaScript-Ausnahmen. Die Testdatei enthält die
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

Zusätzliche Review-Regressionen prüfen eine fehlgeschlagene Übernahme früherer
Entscheidungen mit sichtbaren Werten und Fehlermeldung sowie anschließende Korrektur,
Commit und Reload. Echte Tastatureingaben mit 1.000 synthetischen Dokumenten (rund
2 MB Beschreibungstext) erzeugen während des Tippens keine Vollstate-Snapshots;
nach der Pause wird genau ein Snapshot mit dem letzten Stand geschrieben.
Explizites Speichern, Navigation, Seiten-Lifecycle und Import erzeugen keine
nachträglichen doppelten oder veralteten Timer-Schreibvorgänge. Timer werden für
diese Tests kontrolliert über die Playwright-Browseruhr ausgeführt.

Weitere Parallelitätsprüfungen halten eine echte IndexedDB-Schreibtransaktion
kontrolliert offen, wechseln währenddessen die Ansicht und lassen die Transaktion
erfolgreich abschließen oder abbrechen. Abgebrochene Entscheidungen und Navigation
bleiben auch nach nachfolgender Speicherung und Reload aus dem persistenten State
entfernt. Erfolgreiche Entscheidungen und die zuletzt gewählte Ansicht bleiben erhalten.
Simulierte Reader-Antworten während des Schreibens warten auf dessen Ausgang;
nachgeladene Beobachtungen bleiben sowohl nach Abbruch als auch nach Erfolg erhalten.
Der neue Regressionstest scheiterte zunächst am bisherigen Code und besteht nach
der Umstellung auf isolierte Kandidaten-States und verzögerte parallele Saves.

## Grenzen

Reader-Netzwerkantworten sind simuliert. Wartezeiten der API-Tests werden gezielt
verkürzt; Header-Verarbeitung und Abrufkontrolle werden ausgeführt. Echte Reader-
Authentifizierung, Live-API-Verhalten, große persönliche Bibliotheken und physische
Mobilgeräte wurden nicht geprüft. Das Backup ist weiterhin ein bestätigter kompletter
Restore und kein automatischer Geräteabgleich.

Notion-Coding-Log: wegen fehlender Verbindung nicht geschrieben oder verifiziert;
lokaler Ersatznachweis in `CODING_LOG.md`. Phase-2-Funktionen wurden nicht implementiert.
