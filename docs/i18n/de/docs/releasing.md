<a id="public-connector-release-checklist"></a>
# Release-Checkliste für den öffentlichen Connector

Das öffentliche Repository wird aus
`config/public-blender-connector-files.json` erzeugt. Forke oder kopiere niemals
die private Repository-Historie.

<a id="current-release"></a>
## Aktuelles Release

- Repository: https://github.com/OpenRootdev/vipermesh-blender
- Release-Ziel: https://github.com/OpenRootdev/vipermesh-blender/releases/tag/v1.3.0
- Source-Release-Ziel: `v1.3.0`
- Blender-Kompatibilitätsziel: 5.2
- CI: eigenständiger Typecheck, Konformitätstests, Build, Paketvalidierung, npm
  audit und Add-on-Python-Kompilierung
- Historische Live-Validierung (v1.2.0): persistente stdio-MCP-Discovery,
  Szenenaufrufe, Mutation, gestufte Preview/Finalize, Save, lokale Guidance und
  `execute_code`-Fallback
- Aktuelle Launch-Prüfungen: isolierte Paketkonformität, Inline-Bildtransport,
  Render-only/Preserved-Presentation-Stages, Zurückhalten räumlicher Fehler,
  Dependency-Audit, Python-Kompilierung und Desktop/Mobile-Site-Review. Volle
  Live-Agent-Performance wird im nächsten Demo-Piloten evaluiert.

<a id="before-export"></a>
## Vor dem Export

- Führe `npm run validate:public-blender-connector` aus.
- Führe die fokussierten Tests für das portable MCP-Gateway und die Add-on-UI aus.
- Kompiliere das Add-on mit `python -m py_compile`.
- Installiere das erzeugte Add-on im aktuellen Blender 5.2-Release.
- Verifiziere die UI-Zustände Stopped, Ready, Agent connected und Error.
- Verifiziere Bootstrap, Szeneninspektion, eine Mutation, Preview-Inspection,
  finalen Render, Save und Shutdown über einen frischen MCP-Client.

<a id="export-safety"></a>
## Export-Sicherheit

- Exportiere nur Manifest-Einträge.
- Weise doppelte Ziele, fehlende Dateien, absolute Pfade, Traversal, private
  Anwendungspfade, Secrets, Zugangsdaten, interne Benchmark-Belege und
  wettbewerberspezifischen Provider-Code zurück.
- Scanne das erzeugte Verzeichnis erneut, bevor das GitHub-Repository erstellt wird.
- Erstelle `Ker102/vipermesh-blender` als neues Repository ohne geerbte private Commits.

<a id="release"></a>
## Release

1. Installiere Abhängigkeiten und führe `npm run check` im erzeugten Verzeichnis aus.
2. Paketieren das Add-on als Release-Artefakt.
3. Tagge die Connector-Version.
4. Veröffentliche das MCP-Paket erst, nachdem seine Paketinhalte inspiziert wurden.
5. Pinne das private ViperMesh-Produkt auf die veröffentlichte Connector-Version.
6. Verifiziere den öffentlichen Installationspfad unabhängig.
7. Ändere erst dann die Sichtbarkeit des ViperMesh-Produktrepositorys.
