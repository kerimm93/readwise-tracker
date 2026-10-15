# Reader Log · lokale Triage

Bestehende Single-File-PWA mit Vanilla JavaScript, IndexedDB und Service Worker.
Sprint: **f_n7v28ze4**, Phase 1 der Triage-Spezifikation vom 15.10.2026.

## Start

Im entpackten Verzeichnis:

```sh
python3 -m http.server 8000 --bind 127.0.0.1
```

Im Browser den lokalen Server öffnen. Für PWA/Service Worker localhost oder
HTTPS verwenden; nicht direkt als `file:` öffnen. Es gibt keine App-Pakete,
keinen Build und keine Serverdatenbank. Auf einem Webhost die drei Dateien
`index.html`, `manifest.json` und `sw.js` zusammen bereitstellen.

## Triage

Reader synchronisieren oder ein bestehendes JSON-Backup importieren. Die Ansicht
**Triage** zeigt lokal bekannte Öffnungs- und Fortschrittsbeobachtungen. Interesse,
Routen, Notiz und Reader-Aktionsabsicht sind unabhängig. Ruhen lassen und Verwerfen
schließen alle anderen Routen aus. Keine Auswahl löst Reader-Schreibaktionen aus.

Eingaben werden im Formular sofort übernommen und nach 300 ms Tipp-Pause als Entwurf
lokal gespeichert. Der Status zeigt ausstehende oder fehlgeschlagene Schreibvorgänge.
Kartenwechsel und explizites Speichern schließen die neuesten Eingaben ein; beim
Verlassen der Seite wird ein ausstehender Entwurf zur Speicherung angestoßen. **Speichern & nächste Karte**
übernimmt die Entscheidung erst nach abgeschlossener Speichertransaktion. Noch
nicht bestätigte Entscheidungen und Navigationsänderungen bleiben in einem getrennten
Kandidaten-State; parallele Speichervorgänge warten dessen Ergebnis ab.
**Später entscheiden** verschiebt eine offene Karte ans Ende; **Zurück** und
**Letzte Entscheidung bearbeiten** erlauben Korrekturen. Neue Beobachtungen zu
einem Dokument zeigen dessen frühere Entscheidung zum bewussten Übernehmen.
Eine Entscheidung ohne Route bleibt inhaltlich ein lokaler Entwurf; es gibt in
Phase 1 keinen Exportstatus oder Verarbeitungsstatus.

Die anfängliche Queue ist nach belegtem Zeitpunkt absteigend, dann Reader-ID und
Beobachtungs-ID sortiert. Einträge ohne Datum stehen hinten. Neu entdeckte
Beobachtungen werden untereinander sortiert angehängt, damit laufende Sitzungen
stabil bleiben. Ältere nachgeladene Beobachtungen werden gekennzeichnet und niemals
anhand eines Zeit-Cursors als erledigt übersprungen. Bereits bewertete Karten bleiben
persistiert. Der Reader liefert keine vollständige vergangene Lesesitzungsliste.

## Daten und Backups

State-Version 3 migriert vorhandene States/Backups ohne Triage. Die bestehende
IndexedDB und alle Dokumente, Ereignisse und Lazy-History-Metadaten bleiben erhalten.
Beobachtungen enthalten stabile IDs, Quellenreferenzen und Sortierschlüssel.
Entscheidungen enthalten stabile UUIDs und eine fortlaufende Revision ab 1;
der vollständige lokale Revisionsverlauf steht in `revisions`. Unverändertes
Speichern erhöht die Revision nicht; die Reihenfolge gleicher Routen ist inhaltlich
unerheblich. Notiztexte werden einschließlich Leerzeichen unverändert gespeichert.

JSON-Backup und bestätigter Restore schließen Queue, Entwürfe, Navigation und
Revisionen ein. Restore ersetzt nach Vorschau den gesamten lokalen State, es ist
kein Merge und keine Mehrgeräte-Synchronisierung. Der Readwise-Token bleibt separat
im Browser und wird nicht aus dessen LocalStorage in das Backup übernommen.
Vor einem Gerätewechsel ein Backup exportieren. Beschädigte oder unbekannte
State-Versionen werden abgewiesen, ohne den gespeicherten Original-State zu löschen.

## Tests

Benötigt Python 3, Python-Paket `playwright` und Chromium unter `/usr/bin/chromium`
(in der vorbereiteten Cloud-Umgebung vorhanden):

```sh
python3 tests/triage_browser.py
python3 tests/triage_review_browser.py
```

Die Tests starten einen eigenen temporären HTTP-Server und verwenden ein isoliertes
Browserprofil mit synthetischen Daten. Reader-Antworten werden simuliert. Details
und Grenzen: `TEST_REPORT.md`.

## Folgesprint

Batch-Prompt-Export, Chat-Verarbeitung, Handoff-Import, ReceiptLedger und Hashes
sind nicht implementiert. Es gibt keine Notion-Integration, Reader-Schreibaktionen
oder RPG-/XP-Funktionen. Geplanter Folgesprint bleibt **f_9z0izd51**;
**f_zzd1llsp** betrifft spätere Robustheit, **f_pv3cgbub** bleibt zurückgestellt.
