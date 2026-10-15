# Lokales Coding Log · 15.10.2026

Feature **f_n7v28ze4** · Phase 1 · lokale Triage und persistente Entscheidungsrevisionen.

Das zentrale Notion-Coding-Log konnte mangels verfügbarbarer Notion-Verbindung nicht
frisch gelesen oder fortgeschrieben werden. Dieses lokale Protokoll dokumentiert
nur tatsächlich ausgeführte Arbeit; es ersetzt keinen verifizierten Notion-Eintrag.

- Bestehende App und Produktspezifikation v1.0 analysiert; Single-File-Architektur,
  31-Tage-Erstsync, Lazy History und bestehende API-Limits beibehalten.
- State-Version 3 mit Beobachtungen, deterministischer persistenter Queue, Entwürfen,
  Entscheidungs-UUIDs und unveränderter Revisionshistorie integriert.
- Triage-Ansicht mit Bewertung 0–5, mehrfachen/exklusiven Routen, wortgetreuen Notizen,
  separater lokaler Reader-Aktionsabsicht und persistenter Navigation ergänzt.
- IndexedDB-Schreibqueue auf Transaktionsabschluss umgestellt; Abbrüche sind
  wiederholbar. Import-State wird erst nach erfolgreichem Commit übernommen.
- Explizite Migration, Triage-Validierung, Importvorschau und Backup-Roundtrip
  ergänzt; fehlerhafte States werden nicht durch leere States überschrieben.
- Service-Worker-Cache für die neue App auf `reader-log-v4` erhöht.
- Reproduzierbare Browserregression mit realer IndexedDB, Offline-Reload,
  simulierten Reader-Abrufen und gezielt abgebrochenen Schreibtransaktionen erstellt.
- Beim Test gefundenen Fehler in der Backfill-Kennzeichnung bei vorhandenen
  Beobachtungen ohne Datum korrigiert. Alle abschließenden Tests: siehe Testbericht.

## PR-Review-Korrekturen

- Übernommene frühere Entscheidungen werden vor dem Speicherzugriff im Formular
  angezeigt. Bei Schreibfehlern bleiben sichtbare Felder und In-Memory-Entwurf gleich;
  der Speicherstatus meldet den Fehler. Nachfolgende Korrekturen werden korrekt gespeichert.
- Entwurfsspeicherung um 300 ms verzögert und zusammengefasst, sodass Tastatureingaben
  keine Vollstate-Serialisierung pro Zeichen mehr auslösen. Explizite Saves bündeln
  den ausstehenden Entwurf; Pagehide/Visibilitychange stoßen dessen Speicherung an.
  Backup-Import kann nicht durch einen alten Entwurfstimer überschrieben werden.
- 11 gezielte Browserregressionen mit Schreibfehlern und 1.000 Dokumenten ergänzt;
  die 52 bestehenden Prüfungen erneut erfolgreich ausgeführt (insgesamt 63).
