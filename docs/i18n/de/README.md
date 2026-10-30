<div align="center">

<!-- i18n:languages:start -->
[English](../../../README.md) | [Español](../es/README.md) | [简体中文](../zh-CN/README.md) | [Français](../fr/README.md) | [日本語](../ja/README.md) | [Deutsch](../de/README.md) | [Português (Brasil)](../pt-BR/README.md)
<!-- i18n:languages:end -->

<a href="https://openrootdev.github.io/vipermesh-blender/"><img src="../../../site/assets/brand-mark.png" alt="ViperMesh-Logo" width="104" height="104"></a>

<h1>ViperMesh for Blender</h1>
<p>Open-Source-Blender-MCP-Server und Add-on für KI-Agenten.</p>

[![CI](https://github.com/OpenRootdev/vipermesh-blender/actions/workflows/ci.yml/badge.svg)](https://github.com/OpenRootdev/vipermesh-blender/actions/workflows/ci.yml)
[![GitHub release](https://img.shields.io/github/v/release/Ker102/vipermesh-blender?display_name=tag)](https://github.com/OpenRootdev/vipermesh-blender/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](../../../LICENSE)
[![MCP](https://img.shields.io/badge/Model_Context_Protocol-server-1f6feb)](https://modelcontextprotocol.io/)

**KI-Unterstützung für Blender, mit weniger Code und weniger Warten.**

Entwickelt für schnellere Szenenbearbeitungen, weniger KI-Tokens und besser geprüfte Ergebnisse.

<p>
<a href="https://github.com/OpenRootdev/vipermesh-blender/releases/latest"><img src="../../../site/assets/readme-download.svg" alt="Blender-Add-on herunterladen" width="240" height="44"></a>
<a href="docs/client-setup.md"><img src="../../../site/assets/readme-setup.svg" alt="Einrichtungsanleitung" width="160" height="44"></a>
</p>

[Projektübersicht und Einrichtung](https://openrootdev.github.io/vipermesh-blender/)
| [ViperMesh Studio waitlist](https://vipermesh-studio.vercel.app/waitlist)

</div>

---

ViperMesh for Blender ist ein kostenloser, quelloffener **Blender-MCP-Server und ein Add-on**,
mit dem ein kompatibler KI-Assistent in deiner Blender-Szene arbeiten kann. Es
richtet sich an Blender-Künstler, Hobbyisten und Spieleentwickler, die Hilfe beim
Erstellen und Bearbeiten von 3D-Szenen möchten, nicht noch ein Coding-Projekt.

**Das Ziel: schnellere KI-gestützte Arbeit, weniger KI-Tokens und besser geprüfte Ergebnisse.**
Dein Assistent erhält einsatzbereite Blender-Aktionen, statt für viele gängige
Bearbeitungen neuen Python-Code schreiben zu müssen. Du arbeitest weiter in Blender
und entscheidest, wobei der Assistent helfen soll.

<a id="watch-the-overview"></a>
## Übersicht ansehen

[![Übersicht zu ViperMesh for Blender ansehen](../../../site/assets/connector-overview-poster.png)](https://openrootdev.github.io/vipermesh-blender/#overview)

[Sieh dir das 77-Sekunden-Video an](https://openrootdev.github.io/vipermesh-blender/#overview)
oder [lade die MP4 herunter](https://openrootdev.github.io/vipermesh-blender/assets/connector-overview.mp4).
Sieh, wie dein KI-Client fertige Blender-Aktionen verwendet, warum weniger
generierter Code helfen kann und wie du loslegst. Dies ist eine
illustrierte Übersicht mit Musik, keine zeitlich gemessene Benchmark-Aufzeichnung. GitHubs
README verlinkt auf das abspielbare Video.

<a id="why-vipermesh-for-blender"></a>
## Warum ViperMesh for Blender?

| Was dir wichtig ist | Wie ViperMesh hilft |
| --- | --- |
| Weniger KI-Nutzung | Wiederverwendbare Aktionen reduzieren den Blender-Code, den der Assistent für abgedeckte Aufgaben generieren muss. |
| Weniger Warten | Die Verbindung bleibt offen, und verwandte Aktionen können gemeinsam laufen, statt für jeden Schritt Setup zu wiederholen. |
| Besser geprüfte Szenen | Eingebaute Prüfungen helfen, schwebende Objekte, falsche Orientierungen und Freiraumprobleme zu erkennen; der Assistent kann Bilder inspizieren und Fehler reparieren. |
| Einfacher für deinen Assistenten | Auffindbare Werkzeuge und knappe Guidance erklären, welche Aktionen verfügbar sind und wie man sie verwendet. |
| Raum für individuelle Arbeit | Der Assistent kann weiterhin Python schreiben, wenn deine Anfrage etwas braucht, das die fertigen Werkzeuge nicht abdecken. |

KI-Tokens sind die Texteinheiten, die ein Modell liest und schreibt. Weniger Code
zu generieren kann KI-Nutzung reduzieren, aber Gesamt-Tokens, Kosten und Zeit
hängen auch von deinem Modell und der Aufgabe ab. Szenenprüfungen helfen bei der
Korrektheit; sie garantieren kein schönes oder fehlerfreies Ergebnis.

<a id="one-reference-two-blender-workflows"></a>
## Eine Referenz, zwei Blender-Workflows

<p align="center">
<a href="../../../site/assets/scandinavian-entryway-comparison.png"><img src="../../../site/assets/scandinavian-entryway-comparison.png" alt="Historischer Szenenvergleich: Referenzbild links, ViperMesh MCP Blender-Viewport in der Mitte und originaler BlenderMCP-Viewport rechts" width="960"></a>
</p>

Ein historischer Bildrekonstruktionstest mit dem ViperMesh Blender MCP-Harness
und verfügbaren Assets. Nur die mittlere Überschrift wurde umbenannt; die
Referenz und beide Szenen-Screenshots sind unverändert. Dies ist ein Beispiel,
keine Garantie für jedes Ergebnis. Das öffentliche Add-on bündelt keine privaten
Studio-Asset-Bibliotheken.

[Blender-MCP-Fallstudie lesen, Teil Eins](https://kristoferjussmann.me/case-studies/vipermesh/)
| [Vergleich in voller Größe öffnen](../../../site/assets/scandinavian-entryway-comparison.png)
| [Bildintegritätsdatensatz](../../../site/assets/scandinavian-entryway-comparison.provenance.json)

<a id="what-can-it-help-with"></a>
## Wobei kann es helfen?

- Objekte in einer Szene bauen, bewegen, duplizieren und anordnen.
- Kanten weicher machen, Materialien anpassen, Kameras setzen und Beleuchtung ändern.
- Prüfen, ob Objekte auf ihren Stützen stehen oder genug Abstand lassen.
- Bei Mesh-Bereinigung, Retopologie, UV-Vorbereitung, Rigging und Gewichten unterstützen.
- Mit Animationseinstellungen arbeiten, Exporte vorbereiten und Ergebnisse inspizieren.

Zum Beispiel könntest du deinen Assistenten bitten:

> Move the basket under the right side of the table, without intersecting its legs.

> Soften the sharp edges on this furniture, keeping its overall shape.

> Check this scene for unsupported objects, then show me what needs fixing.

Dies sind Beispiele für Anfragen, keine vorgefertigten Szenenvorlagen. Für die
von den Werkzeugen abgedeckten Operationen musst du Blender-Python nicht selbst schreiben.

<a id="how-is-it-different-from-the-original-blendermcp"></a>
## Wie unterscheidet es sich vom ursprünglichen BlenderMCP?

ViperMesh baut auf dem ursprünglichen
[BlenderMCP-Projekt von Siddharth Ahuja](https://github.com/ahujasid/mcp-for-blender)
auf, das jetzt MCP for Blender heißt. Der Hauptunterschied liegt im Schwerpunkt
auf einem breiten Set fertiger Bearbeitungsaktionen, wiederverwendbarer Workflows
und Szenenprüfungen, statt sich für gängige Bearbeitungen auf neu generiertes
Python zu verlassen.

Beide Projekte können Szenen inspizieren und individuelles Python ausführen. Das
ursprüngliche Projekt bietet außerdem Asset- und Generierungsintegrationen. Das
Ziel von ViperMesh ist, alltägliche Szenenoperationen token-effizienter, schneller,
einfacher für Assistenten nutzbar und leichter validierbar zu machen. Dies ist
keine Behauptung, dass es jede Aufgabe gewinnt oder dass der öffentliche Connector
jedes Feature von ViperMesh Studio enthält.

[Website-Installationsanleitung](https://openrootdev.github.io/vipermesh-blender/setup/) · [Harness Library listing](https://openrootdev.github.io/harness-library/harnesses/vipermesh-blender/)

<a id="requirements"></a>
## Anforderungen

- Blender 5.2 für das derzeit getestete Release-Ziel
- Node.js 20 oder neuer
- Ein MCP-kompatibler Client, der stdio-Server unterstützt

MCP, kurz für Model Context Protocol, ist ein Verbindungsstandard, mit dem ein
KI-Assistent Werkzeuge in einer anderen Anwendung verwenden kann. Du brauchst
eine KI-App, die diese Verbindungen unterstützt; die Installation des Add-ons
allein fügt Blender kein KI-Modell hinzu.

<a id="install"></a>
## Installieren

<a id="1-install-the-blender-addon"></a>
### 1. Das Blender-Add-on installieren

Lade das versionierte Add-on `.py` oder Add-on `.zip` aus dem
[neuesten Release](https://github.com/OpenRootdev/vipermesh-blender/releases/latest)
herunter. In Blender:

1. Öffne **Edit > Preferences > Add-ons**.
2. Wähle **Install from Disk** und wähle die heruntergeladene Python-Datei aus.
3. Aktiviere **ViperMesh for Blender**.
4. Öffne die Seitenleiste des 3D Viewport, wähle **ViperMesh** und klicke
   **Start Local Bridge**.

Lass die Bridge während der gesamten Agent-Sitzung laufen.

<a id="2-install-the-mcp-server"></a>
### 2. Den MCP-Server installieren

**Paketierte Option:** Lade das
[`v1.3.0` MCPB-Bundle](https://github.com/OpenRootdev/vipermesh-blender/releases/download/v1.3.0/vipermesh-blender-1.3.0.mcpb)
herunter und importiere es in einen Client, der lokale MCPB-Erweiterungen
unterstützt. Es enthält den Node-Server und seine Abhängigkeiten, sodass du das
Repository nicht klonen oder bauen musst. Node.js und das separat aktivierte
Blender-Add-on sind weiterhin erforderlich.

Der Connector ist außerdem auf
[Smithery](https://smithery.ai/servers/ker102/vipermesh-blender) und in der
[official MCP Registry](https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.Ker102/vipermesh-blender)
gelistet. Diese Listings verteilen den lokalen Connector, keinen gehosteten
Blender-Dienst. Siehe [Distribution und Bundle-Einrichtung](docs/mcp-distribution.md)
für Prüfsumme, manuelle Extraktionsoption und aktuelle Validierungsgrenzen.

**Source-Option:** Bis das npm-Paket veröffentlicht ist, klone und baue es:

```bash
git clone https://github.com/OpenRootdev/vipermesh-blender.git
cd vipermesh-blender
npm install
npm run build
```

<a id="3-connect-your-ai-assistant"></a>
### 3. Deinen KI-Assistenten verbinden

Bei Verwendung des MCPB-Imports liest der Client seine Launch-Konfiguration aus
dem Bundle. Für die Source-Option verwende den gebauten Einstiegspunkt über einen
absoluten Pfad:

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

Starte diesen Befehl einmal über den MCP-Client. Rufe nicht für jede Blender-
Operation erneut `npm`, `npx` oder `tsx` auf. Siehe [MCP-Client-Einrichtung](docs/client-setup.md)
für Codex, JSON-konfigurierte Clients, Kompatibilität und die optionale Docker MCP
Toolkit-Route.

<a id="technical-details"></a>
## Technische Details

Die folgenden Abschnitte sind für die Einrichtung oder Entwicklung einer KI-
Verbindung. Blender-Benutzer können mit den Installationsschritten und den
Beispielanfragen oben beginnen.

<a id="connection-model"></a>
### Verbindungsmodell

```text
MCP-compatible AI assistant
        |
        | stdio, one long-lived process
        v
ViperMesh MCP server
        |
        | serialized loopback connection
        v
ViperMesh Blender addon (127.0.0.1:9876)
        |
        v
Blender scene
```

Der MCP-Server öffnet keinen Netzwerk-Listener. Das Blender-Add-on lauscht
standardmäßig auf Loopback und meldet **Stopped**, **Ready**, **Agent connected**
oder **Error** in der ViperMesh-Seitenleiste.

<a id="first-agent-calls"></a>
### Erste Agent-Aufrufe

1. Rufe `bootstrap_vipermesh_session` auf.
2. Inspiziere die Szene mit `call_blender_tool(name="get_scene_info")`.
3. Suche Aufgaben-Guidance mit `search_3d_guidance`.
4. Entdecke nur die relevanten Fähigkeiten mit `list_blender_tools`.
5. Baue, inspiziere und repariere, finalisiere und speichere dann.

Die öffentliche MCP-Oberfläche umfasst:

- `bootstrap_vipermesh_session`
- `check_blender_connection`
- `list_blender_tools`
- `call_blender_tool`
- `call_blender_tool_batch`
- `run_blender_scene_stage`
- `get_blender_agent_context`
- `search_3d_guidance`
- `get_3d_guidance_document`

Lies das [vollständige Connector-Handbuch](docs/portable-blender-mcp.md) für
Request-Shapes, Batching-Regeln, gestufte Workflows, lokale Tool-Skills und
Fehlerbehebung. Das Repository liefert außerdem einen installierbaren
[`using-vipermesh-blender` Agent-Skill](skills/using-vipermesh-blender/SKILL.md).

<a id="security"></a>
## Sicherheit

Dieser Connector ist für eine vertrauenswürdige lokale Workstation gedacht.
`execute_code` kann beliebigen Python-Code in Blender ausführen. Verbinde nur
vertrauenswürdige MCP-Clients, belasse die Bridge auf Loopback und prüfe
wirkungsstarke oder destruktive Operationen.

Siehe [SECURITY.md](SECURITY.md) für die Vertrauensgrenze und den privaten Prozess
zur Meldung von Schwachstellen.

<a id="public-connector-scope"></a>
## Umfang des öffentlichen Connectors

Dieses Repository enthält das Open-Source-Blender-Add-on, den portablen MCP-Server,
portable öffentliche Tool-Skills und Connector-Tests. Es enthält nicht die
ViperMesh-Anwendung, Authentifizierung, Abrechnung, private Prompts, private
RAG-Daten, Cloud-Modell-Routing, private Assets, rohe Benchmark-Traces oder
private Evaluierungsdatensätze. Der illustrierte Vergleich ist separat
bereitgestellte öffentliche Evidenz, keine gebündelte Asset-Bibliothek.

Der Connector bündelt keinen kommerziellen 3D-Generierungsanbieter. Neuronale
Generierung kann später über provider-neutrale authentifizierte Dienste ergänzt
werden, ohne Drittanbieter-Zugangsdaten in Blender einzubetten.

<a id="frequently-asked-questions"></a>
## Häufig gestellte Fragen

<a id="do-i-need-a-paid-vipermesh-account"></a>
### Brauche ich ein bezahltes ViperMesh-Konto?

Nein. Das öffentliche Add-on und die lokale Verbindung sind ohne ViperMesh-Konto
kostenlos nutzbar. Deine KI-App oder dein Modellanbieter kann separat Gebühren
erheben. Das Add-on enthält keinen kostenlosen KI-Modellzugang.

<a id="do-i-need-to-be-a-programmer"></a>
### Muss ich programmieren können?

Du musst für die abgedeckten Blender-Bearbeitungen kein Python schreiben. Die
Ersteinrichtung umfasst dennoch die Installation des Add-ons und die Verbindung
einer kompatiblen KI-App. Verwende das MCPB-Bundle in Clients, die es unterstützen,
oder baue mit den bereitgestellten Befehlen aus Source. Die separat aktivierte
Blender-Bridge und die Client-Einrichtung bedeuten, dass dies nicht für jede
Umgebung eine One-Click-Installation ist.

<a id="does-vipermesh-replace-execute_code"></a>
### Ersetzt ViperMesh `execute_code`?

Nein. Es reduziert unnötig generiertes Blender-Python durch strukturierte
Operationen, behält `execute_code` aber für individuelle Geometrie, prozedurale
Effekte, ungewöhnliche Node-Graphs und nicht abgedeckte Workflows bei.

<a id="why-must-the-mcp-process-stay-running"></a>
### Warum muss der MCP-Prozess laufen bleiben?

Der Prozess behält eine serialisierte Verbindung zu Blender. Ihn für jeden Aufruf
neu zu starten, fügt vermeidbaren Startup-, Transport- und Agent-Tool-Overhead hinzu.

<a id="does-it-require-docker"></a>
### Benötigt es Docker?

Nein. Lokale stdio-fähige MCP-Clients starten den Node-Server direkt. Docker MCP
Toolkit ist eine optionale Paketierungs- und Gateway-Route und noch kein
unterstützter ViperMesh-Installationspfad, weil Host-zu-Blender-Loopback-
Konnektivität noch plattformübergreifende Validierung erfordert.

<a id="does-the-public-connector-require-vipermesh-cloud-authentication"></a>
### Benötigt der öffentliche Connector ViperMesh-Cloud-Authentifizierung?

Nein. Das öffentliche Add-on und der lokale MCP-Server funktionieren ohne ViperMesh-
Authentifizierung. Künftige gehostete Modelle und proprietäre Orchestrierung sind
separate Produktfähigkeiten.

<a id="can-it-use-installed-blender-addons"></a>
### Kann es installierte Blender-Add-ons verwenden?

Der Connector kann installierte Add-ons inspizieren und unterstützt vertrauenswürdige
lokale Automatisierung. Unbekannte Add-on-Operationen sollten geprüft werden,
bevor sie als aufrufbare Agent-Fähigkeiten bereitgestellt werden.

<a id="development"></a>
## Entwicklung

```bash
npm install
npm run check
python -m py_compile addon/vipermesh-addon.py
```

Siehe [CONTRIBUTING.md](CONTRIBUTING.md), bevor du einen Pull Request öffnest.

<a id="license-and-attribution"></a>
## Lizenz und Attribution

ViperMesh for Blender wird unter der [MIT License](../../../LICENSE) veröffentlicht. Es enthält
Arbeit, die von [BlenderMCP](https://github.com/ahujasid/mcp-for-blender) von
Siddharth Ahuja abgeleitet ist. Siehe [NOTICE.md](NOTICE.md) für Attribution und
Markenhinweise.
