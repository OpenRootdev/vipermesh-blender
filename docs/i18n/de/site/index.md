<a id="vipermesh-blender-mcp-server-and-addon"></a>
# ViperMesh: Blender MCP-Server und Add-on

> Kostenlose, quelloffene lokale KI-Unterstützung für Blender-Szenenbearbeitung, Inspektion und wiederverwendbare 3D-Operationen.

Kanonische Seite: https://openrootdev.github.io/vipermesh-blender/
Repository: https://github.com/OpenRootdev/vipermesh-blender
Lizenz: MIT, mit Upstream-Attribution in NOTICE.md.

ViperMesh verwendet zwei lokale Teile. Ein kompatibler KI-Client startet einen
persistent Node-MCP-Prozess über stdio. Dieser Prozess verbindet sich über eine
serialisierte Loopback-TCP-Bridge mit dem Blender-Add-on, standardmäßig
127.0.0.1:9876.

Fertige Aktionen decken Szenenanordnung, Materialien, Beleuchtung, Kameras,
Geometrie- und UV-Vorbereitung, Rigging, Gewichte, Animationsoperationen, Export
und Diagnosen ab. Neun Top-Level-MCP-Werkzeuge stellen diese Fähigkeiten bereit.
Agenten sollten zuerst bootstrap_vipermesh_session aufrufen. Python-Ausführung
bleibt für individuelle Arbeit verfügbar.

Szenenprüfungen und visuelle Inspektion helfen einem Agenten, seine Arbeit zu
reparieren. Weniger generierte Tokens, schnellere Arbeit und bessere Ergebnisse
sind Ziele, keine universellen Garantien. Ergebnisse hängen vom Modell, von der
Szene und von der Aufgabe ab.

Der Connector ist kein gehostetes Generierungsmodell. Er enthält kein KI-Modell,
kein Cloud-Routing, keine privaten Studio-Asset-Bibliotheken, keine Authentifizierung
und keine Abrechnung. Docker und ein ViperMesh-Konto sind nicht erforderlich;
Modellzugriff kann separat kostenpflichtig sein. Er ist ein vertrauenswürdiger
lokaler Connector, keine Sandbox.

<a id="install"></a>
## Installieren

Blender 5.2 ist das derzeit getestete Release-Ziel. Node.js 20+ und ein Client,
der lokales stdio-MCP unterstützt, sind erforderlich. Aktiviere das separate
Blender-Add-on und starte die lokale Bridge. Importiere das MCPB-Bundle in einem
unterstützten Client oder baue den Source und registriere den gebauten Einstiegspunkt.
Halte einen Prozess für die Sitzung am Laufen.

- [Installation und Fehlerbehebung](https://openrootdev.github.io/vipermesh-blender/setup/index.md)
- [Client-Konfiguration](https://github.com/OpenRootdev/vipermesh-blender/blob/main/docs/client-setup.md)
- [Release-Bundles](https://github.com/OpenRootdev/vipermesh-blender/releases)
- [Connector-Handbuch](https://github.com/OpenRootdev/vipermesh-blender/blob/main/docs/portable-blender-mcp.md)
- [Agent-Skill](https://github.com/OpenRootdev/vipermesh-blender/blob/main/skills/using-vipermesh-blender/SKILL.md)
- [Sicherheitsgrenze](https://github.com/OpenRootdev/vipermesh-blender/blob/main/SECURITY.md)
- [Illustrierte Übersicht](https://openrootdev.github.io/vipermesh-blender/#overview)
- [Harness Library](https://openrootdev.github.io/harness-library/harnesses/vipermesh-blender/)
