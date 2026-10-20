<a id="install-vipermesh-blender-mcp"></a>
# Installer ViperMesh Blender MCP

Page canonique : https://openrootdev.github.io/vipermesh-blender/setup/



← Présentation ViperMesh

Installez ViperMesh for Blender.

Connectez un client IA à votre scène Blender locale avec le serveur MCP et
l'addon.




Ce dont vous avez besoin

Blender 5.2 est la cible de version actuellement testée.

Node.js 20 ou plus récent.

Un client IA qui prend en charge les serveurs MCP locaux sur stdio. Un client
qui accepte uniquement des URL de serveur distant ne peut pas se connecter
directement à cette version.

Le connecteur est gratuit et sous licence MIT. Votre client ou modèle IA peut
facturer séparément. Docker et un compte ViperMesh ne sont pas requis.




1. Activer l'addon Blender

Téléchargez le fichier Python d'addon versionné ou le ZIP depuis la dernière
version. Dans Blender, ouvrez Edit → Preferences → Add-ons → Install from Disk,
sélectionnez le fichier et activez ViperMesh for Blender.

Ouvrez la barre latérale du 3D Viewport, sélectionnez ViperMesh et cliquez sur
Start Local Bridge. Laissez Blender et le pont en cours d'exécution. La
connexion par défaut est 127.0.0.1:9876.




2. Installer le serveur MCP local

Installation packagée

Téléchargez le bundle MCPB v1.3.0 et sa somme de contrôle SHA-256. Importez-le
dans un client qui prend en charge les extensions MCPB locales. Le bundle inclut
le serveur Node et les dépendances ; Node.js et l'addon Blender séparé restent
requis.

Sans importateur MCPB, extrayez le bundle comme ZIP dans un répertoire
permanent. Configurez votre client pour lancer node avec le chemin absolu vers
server/index.mjs. Suivez le guide du bundle et de la somme de contrôle.

Construire depuis les sources

git clone https://github.com/OpenRootdev/vipermesh-blender.git
cd vipermesh-blender
npm install
npm run build




3. Connecter votre client IA

Pour la construction source, enregistrez le serveur une seule fois avec le point
d'entrée construit. Remplacez le chemin d'exemple par votre propre chemin absolu :

{
  "mcpServers": {
    "vipermesh-blender": {
      "command": "node",
      "args": ["C:/absolute/path/to/vipermesh-blender/dist/public-portable-blender-mcp.js"]
    }
  }
}

Les emplacements de configuration et les clés de premier niveau dépendent du
client. Voir le guide de configuration client et la documentation de votre
client. Le client doit garder un seul processus MCP actif pendant toute la
session.




4. Vérifier la connexion, puis essayer une petite modification

Demandez à votre agent d'appeler bootstrap_vipermesh_session en premier et
d'inspecter le résultat de connexion. Commencez par une petite demande, comme
déplacer un objet ou vérifier s'il repose sur son support. Inspectez la scène et
les images résultantes avant de faire confiance à la modification.

Neuf outils MCP de premier niveau exposent la découverte, les opérations de
scène, les vérifications et le fallback Python. Ce n'est pas un modèle de
génération 3D hébergé, et le connecteur public n'inclut pas les bibliothèques
d'assets Studio privées.




Problèmes de configuration courants

Mon client ne voit pas les outils

Vérifiez la commande enregistrée et le chemin absolu du fichier. Confirmez que
votre client prend en charge les serveurs MCP stdio locaux et peut lancer Node.
Rechargez la connexion MCP du client selon ses propres instructions.

Les outils apparaissent, mais Blender ne se connecte pas

Confirmez que Blender est ouvert, que l'addon est activé et que Start Local
Bridge est actif. Gardez les ports du serveur et du pont d'addon cohérents.
Gardez le pont sur loopback ; ne l'exposez pas publiquement.

L'assistant redémarre sans cesse le serveur

Configurez le client pour gérer un sous-processus persistant unique. Exécuter
npm, npx ou tsx séparément pour chaque appel d'outil abandonne la session
existante.

La connexion est-elle sandboxée ?

Non. C'est un connecteur local de confiance. Le fallback Python peut exécuter du
code dans Blender. Utilisez des clients de confiance et examinez les opérations
destructrices. Lisez la limite de sécurité.


Signaler un problème de configuration · Documentation pour les agents · Liste Harness Library

Configuration client : https://github.com/OpenRootdev/vipermesh-blender/blob/main/docs/client-setup.md
Bundle et sommes de contrôle : https://github.com/OpenRootdev/vipermesh-blender/blob/main/docs/mcp-distribution.md
Sécurité : https://github.com/OpenRootdev/vipermesh-blender/blob/main/SECURITY.md
