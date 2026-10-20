<a id="mcp-distribution"></a>
# MCP-Distribution

ViperMesh for Blender wird als lokaler stdio-Connector veröffentlicht. Es hostet
Blender nicht, stellt kein KI-Modell bereit und enthält weder das private
ViperMesh Studio noch dessen vollständiges benchmarked harness.

<a id="published-listings"></a>
## Veröffentlichte Listings

- [Smithery: ker102/vipermesh-blender](https://smithery.ai/servers/ker102/vipermesh-blender)
- [Official MCP Registry: io.github.Ker102/vipermesh-blender](https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.Ker102/vipermesh-blender)
- [GitHub release v1.3.0](https://github.com/OpenRootdev/vipermesh-blender/releases/tag/v1.3.0)

Die offizielle Registry hostet Metadaten. Das MCPB-Paket wird im GitHub-Release
gehostet. Smitherys Listing enthält ebenfalls dasselbe Bundle und die neun
MCP-Tool-Schemas, die vom paketierten Server entdeckt wurden.

<a id="bundle-setup"></a>
## Bundle-Einrichtung

1. Installiere und aktiviere das Blender-Add-on mithilfe der [Hauptinstallationsanleitung](../README.md#install).
2. Lade [vipermesh-blender-1.3.0.mcpb](https://github.com/OpenRootdev/vipermesh-blender/releases/download/v1.3.0/vipermesh-blender-1.3.0.mcpb)
   und die zugehörige [SHA-256-Datei](https://github.com/OpenRootdev/vipermesh-blender/releases/download/v1.3.0/vipermesh-blender-1.3.0.mcpb.sha256) herunter.
3. Importiere das Bundle in einen MCPB-kompatiblen Client und befolge dessen
   lokale Erweiterungsanweisungen. Node.js wird von der Launch-Konfiguration des
   Bundles benötigt. Belasse den Bridge-Port bei `9876`, sofern dein Add-on
   keinen anderen Port verwendet.
4. Starte die lokale Blender-Bridge, rufe dann `bootstrap_vipermesh_session`
   aus dem KI-Client auf und inspiziere das Verbindungsergebnis.

Clients ohne MCPB-Importe können die [Quellinstallation](client-setup.md) verwenden.
Alternativ ist das MCPB ein ZIP-Archiv: Extrahiere es in ein dauerhaftes
Verzeichnis und registriere `node` mit dem absoluten Pfad zu `server/index.mjs`
als Argument. Das extrahierte Paket enthält seine Runtime-Abhängigkeiten und
lokale Guidance; kein `npm install` ist erforderlich. Starte es einmal als
persistenten stdio-Subprozess, nicht einmal pro Blender-Operation.

Die Bridge bleibt auf `127.0.0.1`. Remote-only Clients können diesen lokalen
Connector nicht direkt verwenden. Stelle Blenders Bridge nicht öffentlich bereit,
um sie zur Verbindung zu bringen.

<a id="release-integrity-and-validation"></a>
## Release-Integrität und Validierung

Version `1.3.0` ist aus dem Source-Commit
`781700be4f0fb32b135d3f5cb7da012ce8fc4abd` gebaut.

Bundle SHA-256:

```text
45f8cee90540e9f906b8e817efb6fa0a1302f8dba515522dc3682d328a90206c
```

Source-TypeScript- und Konformitätsprüfungen, Add-on-Python-Syntax,
Package-Schema-Validierung, MCP-Initialisierung, Nine-Tool-Discovery und lokale
Guidance-Lookups wurden bestanden. Der Release-Download wurde vor der Registry-
Veröffentlichung gegen diese Prüfsumme geprüft.

Diese Paketprüfungen belegen keine Live-Blender-Kompatibilität für jeden Client.
Ein Live-Szenentest und ein End-to-End-MCPB-Installationstest stehen für dieses
Bundle noch aus. Teste in einer Wegwerf-Szene, prüfe destruktive Operationen und
befolge die [Sicherheitshinweise](../SECURITY.md).

<a id="maintainer-notes"></a>
## Maintainer-Hinweise

Die veröffentlichten Registry-Metadaten werden in [server.json](../../../../server.json) verfolgt.
Für ein neues Release baue und validiere das Bundle erneut, lade seine exakten
Bytes und Prüfsumme in das Release hoch und aktualisiere dann Version, Source-
Commit, Download-URL und Hash gemeinsam, bevor du Metadaten veröffentlichst.

Das MCPB-Manifest listet Tool-Namen auf. Smithery-Veröffentlichung benötigt
zusätzlich die vollständigen `tools/list`-Schemas aus dem paketierten Server;
Namen allein erfüllen seine Server-Card-Validierung nicht. Halte diese Schemas
mit dem Release konsistent, statt Tool-Definitionen zu erfinden oder wegzulassen.
