<a id="install-vipermesh-blender-mcp"></a>
# ViperMesh Blender MCP installieren

Kanonische Seite: https://openrootdev.github.io/vipermesh-blender/setup/



← ViperMesh-Übersicht

Installiere ViperMeshfor Blender.

Verbinde einen KI-Client über MCP-Server und Add-on mit deiner lokalen Blender-Szene.




Was du brauchst

Blender 5.2 ist das derzeit getestete Release-Ziel.

Node.js 20 oder neuer.

Ein KI-Client, der lokale MCP-Server über stdio unterstützt. Ein Client, der nur Remote-Server-URLs akzeptiert, kann sich nicht direkt mit diesem Release verbinden.

Der Connector ist kostenlos und MIT-lizenziert. Dein KI-Client oder Modell kann separat kostenpflichtig sein. Docker und ein ViperMesh-Konto sind nicht erforderlich.




1. Das Blender-Add-on aktivieren

Lade die versionierte Add-on-Python-Datei oder ZIP aus dem neuesten Release herunter. Öffne in Blender Edit → Preferences → Add-ons → Install from Disk, wähle die Datei aus und aktiviere ViperMesh for Blender.

Öffne die Seitenleiste des 3D Viewport, wähle ViperMesh und klicke Start Local Bridge. Lass Blender und die Bridge laufen. Die Standardverbindung ist 127.0.0.1:9876.




2. Den lokalen MCP-Server installieren

Paketierte Installation

Lade das v1.3.0 MCPB-Bundle und seine SHA-256-Prüfsumme herunter. Importiere es in einen Client, der lokale MCPB-Erweiterungen unterstützt. Das Bundle enthält den Node-Server und Abhängigkeiten; Node.js und das separate Blender-Add-on sind weiterhin erforderlich.

Ohne MCPB-Importer extrahiere das Bundle als ZIP in ein dauerhaftes Verzeichnis. Konfiguriere deinen Client so, dass er node mit dem absoluten Pfad zu server/index.mjs startet. Folge der Bundle- und Prüfsummen-Anleitung.

Aus Source bauen

git clone https://github.com/OpenRootdev/vipermesh-blender.git
cd vipermesh-blender
npm install
npm run build




3. Deinen KI-Client verbinden

Registriere für den Source-Build den Server einmal mit dem gebauten Einstiegspunkt. Ersetze den Beispielpfad durch deinen eigenen absoluten Pfad:

{
  "mcpServers": {
    "vipermesh-blender": {
      "command": "node",
      "args": ["C:/absolute/path/to/vipermesh-blender/dist/public-portable-blender-mcp.js"]
    }
  }
}

Konfigurationsorte und Top-Level-Keys hängen vom Client ab. Siehe die Client-Einrichtungsanleitung und die Dokumentation deines Clients. Der Client sollte einen MCP-Prozess für die vollständige Sitzung am Leben halten.




4. Die Verbindung prüfen, dann eine kleine Bearbeitung ausprobieren

Bitte deinen Agenten, zuerst bootstrap_vipermesh_session aufzurufen und das Verbindungsergebnis zu inspizieren. Beginne mit einer kleinen Anfrage, etwa dem Verschieben eines Objekts oder der Prüfung, ob es auf seiner Stütze steht. Inspiziere die resultierende Szene und Bilder, bevor du der Bearbeitung vertraust.

Neun Top-Level-MCP-Werkzeuge stellen Discovery, Szenenoperationen, Prüfungen und den Python-Fallback bereit. Dies ist kein gehostetes 3D-Generierungsmodell, und der öffentliche Connector enthält keine privaten Studio-Asset-Bibliotheken.




Häufige Einrichtungsprobleme

Mein Client kann die Werkzeuge nicht sehen

Prüfe den registrierten Befehl und den absoluten Dateipfad. Bestätige, dass dein Client lokale stdio-MCP-Server unterstützt und Node starten kann. Lade die MCP-Verbindung des Clients gemäß seinen eigenen Anweisungen neu.

Die Werkzeuge erscheinen, aber Blender verbindet sich nicht

Bestätige, dass Blender geöffnet, das Add-on aktiviert und Start Local Bridge aktiv ist. Halte Server- und Add-on-Bridge-Ports konsistent. Belasse die Bridge auf Loopback; stelle sie nicht öffentlich bereit.

Der Assistent startet den Server ständig neu

Konfiguriere den Client so, dass er einen persistenten Subprozess verwaltet. Das separate Ausführen von npm, npx oder tsx für jeden Werkzeugaufruf verwirft die vorhandene Sitzung.

Ist die Verbindung sandboxed?

Nein. Dies ist ein vertrauenswürdiger lokaler Connector. Der Python-Fallback kann Code in Blender ausführen. Verwende vertrauenswürdige Clients und prüfe destruktive Operationen. Lies die Sicherheitsgrenze.


Einrichtungsproblem melden · Dokumentation für Agenten · Harness Library-Listing

Client-Konfiguration: https://github.com/OpenRootdev/vipermesh-blender/blob/main/docs/client-setup.md
Bundle und Prüfsummen: https://github.com/OpenRootdev/vipermesh-blender/blob/main/docs/mcp-distribution.md
Sicherheit: https://github.com/OpenRootdev/vipermesh-blender/blob/main/SECURITY.md
