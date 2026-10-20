<a id="changelog"></a>
# Änderungsprotokoll

Alle nennenswerten Änderungen an ViperMesh for Blender werden hier dokumentiert.

<a id="unreleased"></a>
## [Unveröffentlicht]

<a id="130---2026-10-07"></a>
## [1.3.0] - 2026-10-07

<a id="added"></a>
### Hinzugefügt

- Mit dem Repository verbundene GitHub-Pages-Übersicht, Einrichtung und ehrliche Fähigkeitsgrenzen.
- Inline begrenzte PNG/JPEG-Ausgabe für bildfähige MCP-Clients.
- Geometrie-/Deformationsdiagnosen und geschützte Add-on-Operationen, die bereits
  in der aktuellen Blender-Werkzeugoberfläche vorhanden sind, in die öffentliche Distribution synchronisiert.

<a id="changed"></a>
### Geändert

- Finalize kann vorhandene Kamera/Beleuchtung bewahren und rendern, ohne eine blend-
  Datei zu speichern. Benannte räumliche Fehler blockieren die finale Ausgabe und behalten Reparaturdetails.
- Feste Vorschauzahlen entfernt; aufgabenbasierte visuelle Prüfung verlangen und
  ungelöste Defekte offenlegen, statt Dateigesundheit als Qualitätsurteil zu behandeln.
- Blend-Speicherungen sind explizit und lehnen vorhandene Ziele beim gestuften Finalize ab.
- Öffentliche Dependency-Lock-Datei und SDK-Untergrenze aktualisiert; Clean-Install-Audit ist sauber.
- Paketvalidierung prüft jede ausgelieferte Skill-Referenz.
- Retarget-Rollback nach Backup- oder Exportfehler, Teilimport-Bereinigung,
  Behandlung abgebrochener Operatoren, Enum-Flag-Argumentkonvertierung und
  implementierungsbewusste Add-on-Fingerprints korrigiert. Blender-Laufzeitregressionen hinzugefügt.

<a id="changed-1"></a>
### Geändert

- Exportierten privaten Tool-Guide-Korpus durch einen knappen, installierbaren
  öffentlichen Agent-Skill und anpassbare Referenzdokumente ersetzt.
- Explizite native stdio-Client-Einrichtung hinzugefügt und die optionale,
  noch nicht unterstützte Docker MCP Toolkit-Route klargestellt.
- Exportprüfungen hinzugefügt, die verhindern, dass private `data/tool-guides`-
  Inhalte in öffentliche Releases gelangen.

<a id="120---2026-07-25"></a>
## [1.2.0] - 2026-07-25

<a id="added-1"></a>
### Hinzugefügt

- Persistenter stdio-MCP-Server mit einer serialisierten Blender-Verbindung pro
  Agent-Sitzung.
- Blender-Add-on mit expliziten Zuständen Stopped, Ready, Agent connected und Error.
- Deterministische Szeneninspektion sowie Werkzeuge für Assembly, Materialien,
  Beleuchtung, Kamera, Rendering, Animation, Rigging, UV, Export und Retopologie.
- Begrenzte Batch-Aufrufe und gestufte Build-, Preview-Inspection- und Finalize-
  Workflows.
- Sitzungs-Bootstrap, MCP-Ressourcen, kompakter Betriebskontext und eingecheckte
  Aufgaben-Guidance für neue Agenten.
- Expliziter `execute_code`-Fallback für wirklich individuelle Blender-Arbeiten.
- Nur lokale Loopback-Übertragung und öffentliche Release-Validierung.

[Unveröffentlicht]: https://github.com/OpenRootdev/vipermesh-blender/compare/v1.3.0...HEAD
[1.3.0]: https://github.com/OpenRootdev/vipermesh-blender/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/OpenRootdev/vipermesh-blender/releases/tag/v1.2.0
