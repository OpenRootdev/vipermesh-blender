<a id="mcp-client-setup"></a>
# MCP-Client-Einrichtung

<a id="what-starts-what"></a>
## Was was startet

ViperMesh for Blender hat zwei lokale Verbindungen:

1. Ein MCP-Client startet den ViperMesh Node-Server als langlebigen stdio-
   Subprozess.
2. Der Node-Server öffnet und verwendet eine serialisierte TCP-Verbindung zum Blender-
   Add-on auf `127.0.0.1:9876` wieder.

Der MCP-Client ist für den Server-Lebenszyklus verantwortlich. Registriere den
Server einmal im Client und verwende dann die in dieser Client-Sitzung
bereitgestellten MCP-Werkzeuge. Das Ausführen eines separaten `npm`-, `npx`- oder
`tsx`-Befehls für jeden Werkzeugaufruf erzeugt einen neuen Serverprozess und
verwirft die persistente Verbindung.

Docker ist für Clients, die lokale stdio-MCP-Server unterstützen, nicht erforderlich.

<a id="native-stdio-setup"></a>
## Native stdio-Einrichtung

Repository klonen, installieren und bauen:

```bash
git clone https://github.com/OpenRootdev/vipermesh-blender.git
cd vipermesh-blender
npm install
npm run build
```

Verwende den gebauten Einstiegspunkt über einen absoluten Pfad. Dadurch vermeidest
du die Abhängigkeit von einer clientspezifischen Arbeitsverzeichnis-Option.

<a id="codex"></a>
### Codex

```bash
codex mcp add vipermesh-blender -- node C:/absolute/path/to/vipermesh-blender/dist/public-portable-blender-mcp.js
```

Registrierung bestätigen:

```bash
codex mcp list
```

Öffne eine neue Codex-Aufgabe, wenn die aktuelle Aufgabe MCP-Registrierungen nicht neu lädt.

<a id="json-configured-clients"></a>
### JSON-konfigurierte Clients

Clients wie Claude Desktop und andere Hosts akzeptieren häufig einen Befehl und
ein Argument-Array:

```json
{
  "mcpServers": {
    "vipermesh-blender": {
      "command": "node",
      "args": [
        "C:/absolute/path/to/vipermesh-blender/dist/public-portable-blender-mcp.js"
      ]
    }
  }
}
```

Der Konfigurationsdateiname und der Top-Level-Key unterscheiden sich je nach
Client. Verwende die aktuelle MCP-Dokumentation des Clients, aber halte den
Befehl selbst äquivalent.

<a id="client-compatibility"></a>
## Client-Kompatibilität

Ein Client kann dieses Release direkt verwenden, wenn er lokale MCP-Server über
stdio unterstützt und einen Subprozess starten kann. MCP-Unterstützung allein
garantiert nicht, dass:

- manche Clients lokales stdio und remote Streamable HTTP unterstützen;
- manche nur Remote-Server-URLs unterstützen;
- manche ein Plugin, eine Erweiterung oder eine Administratorrichtlinie benötigen,
  bevor lokale Prozessausführung erlaubt ist.

Dieses Release ist stdio-only. Ein remote-only Client benötigt einen separat
gehosteten MCP-Transport oder ein kompatibles Gateway; er kann sich nicht direkt
mit dem TCP-Protokoll des Blender-Add-ons verbinden.

<a id="docker-mcp-toolkit"></a>
## Docker MCP Toolkit

Docker MCP Toolkit kann containerisierte MCP-Server zentralisieren und sein
stdio-Gateway mit unterstützten Clients verbinden. Es ist eine optionale
Distributionsroute, keine Voraussetzung für ViperMesh.

ViperMesh veröffentlicht derzeit keinen Docker MCP Catalog-Eintrag. Das Blender-
Add-on bleibt aus lokaler Sicherheitsgründen ebenfalls loopback-only. Ein Container
muss diesen Host-Loopback-Dienst zuverlässig erreichen, was je nach Docker-Host,
Netzwerkmodus und Client-Umgebung variiert.

Aus diesem Grund ist natives stdio heute die unterstützte Einrichtung. Stelle die
Blender-Bridge nicht auf einer öffentlichen Schnittstelle bereit, nur damit sich
ein Container verbinden kann. Docker Toolkit-Anweisungen werden zu einem
unterstützten Pfad erhoben, nachdem ein End-to-End-Konnektivitätstest unter
Windows, macOS und Linux eine sichere Konfiguration definiert hat.

Offizielle Referenzen:

- [MCP transports](https://modelcontextprotocol.io/specification/latest/basic/transports)
- [Docker MCP Toolkit](https://docs.docker.com/ai/mcp-catalog-and-toolkit/)

<a id="verify-the-session"></a>
## Die Sitzung verifizieren

1. Starte Blender und die lokale ViperMesh-Bridge.
2. Öffne eine neue Sitzung im konfigurierten MCP-Client.
3. Rufe `bootstrap_vipermesh_session` auf.
4. Bestätige, dass `connection.connected` `true` ist und `sessionModel`
   `persistent` ist.
5. Mache zwei leichte Inspektionsaufrufe. Sie sollten einen MCP-Prozess und
   einen Blender-Client wiederverwenden, statt neue Shell-Befehle zu starten.
