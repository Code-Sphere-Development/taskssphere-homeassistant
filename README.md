# TasksSphere für Home Assistant

Bindet eine [TasksSphere](https://github.com/Code-Sphere-Development/TasksSphere)-Instanz als To-do-Listen, Sensoren und Kalender in Home Assistant ein.

## Einbinden

Dieses Repository ist **privat**. HACS kann private Repositories nur lesen, wenn in HACS ein GitHub-Token mit `repo`-Berechtigung hinterlegt ist. Ohne diesen Token findet HACS das Repository nicht und meldet lediglich, es sei nicht vorhanden — die Suche danach führt sonst in die Irre.

1. In HACS unter *Integrationen* das Dreipunktmenü öffnen, **Benutzerdefinierte Repositories**.
2. `Code-Sphere-Development/taskssphere-homeassistant` eintragen, Kategorie *Integration*.
3. Installieren, Home Assistant neu starten.

Ohne HACS: den Ordner `custom_components/taskssphere` nach `config/custom_components/` kopieren und neu starten.

## Einrichten

*Einstellungen → Geräte & Dienste → Integration hinzufügen → TasksSphere*

Gefragt werden zwei Dinge:

- **Adresse** der Instanz, etwa `https://tasks.example.org`
- **Token**, erzeugt in TasksSphere unter *Profil → API-Token*

Das Passwort wird nicht benötigt und nicht gespeichert. Der Token wird sofort gegen `GET /api/profile` geprüft; schlägt das fehl, kommt die Einrichtung gar nicht erst zustande.

Das Abrufintervall steht auf fünf Minuten und lässt sich über *Konfigurieren* am Eintrag ändern.

## Was entsteht

| Entität | Herkunft |
|---|---|
| Eine To-do-Liste je **Checkliste** | `task_lists` vom Typ `checklist` |
| To-do-Liste **Aufgaben** | alle offenen Aufgaben, dazu die jüngsten Erledigungen |
| Sensor **Überfällig** | offene Aufgaben mit Fälligkeit in der Vergangenheit |
| Sensor **Heute fällig** | offene Aufgaben mit Fälligkeit heute |
| Sensor **Heute erledigt** | Erledigungen von heute |
| Kalender **Termine** | `GET /api/tasks/occurrences`, Wiederholungen aufgelöst |

Checklisten kennen in TasksSphere kein Fälligkeitsdatum. Diese Listen melden Home Assistant deshalb bewusst kein Datumsfeld, statt eines anzubieten, das hinterher nicht ankommt. Die Notiz eines Eintrags erscheint als Beschreibung.

## Grenzen, die aus der API stammen

Diese Punkte sind keine Nachlässigkeit der Integration, sondern Eigenschaften der Schnittstelle. Sie stehen hier, damit niemand den Fehler an der falschen Stelle sucht.

**Der Sensor „Heute erledigt" kann zu niedrig stehen.** `GET /api/tasks/completed` liefert höchstens zehn Einträge, serverseitig fest verdrahtet. Wer an einem Tag mehr abhakt, sieht die Zahl bei zehn stehenbleiben.

**Nur die jüngsten zehn Erledigungen lassen sich zurücknehmen.** Aus demselben Grund: Was nicht mehr in dieser Liste steht, erscheint in Home Assistant nicht als erledigter Eintrag und kann dort folglich nicht wieder aufgemacht werden. In TasksSphere selbst geht es weiterhin.

**Einträge lassen sich nicht umsortieren.** Die API kennt zwar ein Feld für die Position, aber keinen Weg, mehrere Einträge in einem Zug neu zu ordnen. Eine halbgare Umsetzung würde Reihenfolgen durcheinanderbringen, deshalb meldet die Integration die Fähigkeit erst gar nicht.

**Zeitpunkte haben keine Zonenangabe.** TasksSphere liefert `2026-09-15 08:00:00` ohne Zonenmarker; der Wert ist Wanduhrzeit in der Zeitzone der Aufgabe. Die Integration verankert ihn in der Zeitzone von Home Assistant. Im selben Haushalt ist das dasselbe — bei Aufgaben in fremden Zeitzonen kann es um Stunden danebenliegen.

**Je Checkliste eine Anfrage.** Die Übersicht liefert die Einträge nicht mit, also holt der Koordinator jede Checkliste einzeln. Bei fünf Listen sind das sieben Anfragen je Zyklus. Im Haushalt unbedenklich, bei vielen Listen wäre ein Sammelendpunkt in TasksSphere die bessere Antwort.

## Markenzeichen

Icon und Bildmarke liegen unter `custom_components/taskssphere/brand/`. HACS sucht dort zuerst und weicht erst danach auf das Marken-Repository von Home Assistant aus, in dem TasksSphere nicht eingetragen ist.

## Voraussetzungen

- Home Assistant 2025.2 oder neuer
- TasksSphere mit dem Endpunkt `POST /api/tasks/{task}/uncomplete` — ohne ihn lässt sich ein Haken nicht wieder entfernen

## Entwicklung

```bash
python3.13 -m venv .venv
.venv/bin/pip install homeassistant pytest-homeassistant-custom-component
.venv/bin/pytest
```

## Lizenz

MIT
