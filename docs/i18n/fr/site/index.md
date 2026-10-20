<a id="vipermesh-blender-mcp-server-and-addon"></a>
# ViperMesh : serveur MCP Blender et addon

> Assistance IA locale, gratuite et open source pour l'édition, l'inspection et les opérations 3D réutilisables dans les scènes Blender.

Page canonique : https://openrootdev.github.io/vipermesh-blender/
Dépôt : https://github.com/OpenRootdev/vipermesh-blender
Licence : MIT, avec attribution amont dans NOTICE.md.

ViperMesh utilise deux composants locaux. Un client IA compatible lance un
processus MCP Node persistant sur stdio. Ce processus se connecte à l'addon
Blender par un pont TCP loopback sérialisé, par défaut 127.0.0.1:9876.

Des actions prêtes à l'emploi couvrent l'agencement de scène, les matériaux,
l'éclairage, les caméras, la géométrie et la préparation UV, le rigging, les
poids, les opérations d'animation, l'export et les diagnostics. Neuf outils MCP
de premier niveau exposent ces capacités. Les agents doivent appeler
bootstrap_vipermesh_session en premier. L'exécution Python reste disponible pour
le travail personnalisé.

Les vérifications de scène et l'inspection visuelle aident un agent à réparer
son travail. Moins de tokens générés, un travail plus rapide et de meilleurs
résultats sont des objectifs, pas des garanties universelles. Les résultats
dépendent du modèle, de la scène et de la tâche.

Le connecteur n'est pas un modèle de génération hébergé. Il n'inclut pas de
modèle IA, de routage cloud, de bibliothèques d'assets Studio privées,
d'authentification ni de facturation. Docker et un compte ViperMesh ne sont pas
requis ; l'accès au modèle peut coûter séparément. C'est un connecteur local de
confiance, pas un bac à sable.

<a id="install"></a>
## Installation

Blender 5.2 est la cible de version actuellement testée. Node.js 20+ et un
client capable d'exécuter MCP local sur stdio sont requis. Activez l'addon
Blender séparé et démarrez le pont local. Importez le bundle MCPB dans un client
pris en charge, ou construisez la source et enregistrez le point d'entrée
construit. Gardez un seul processus actif pendant la session.

- [Installation et dépannage](https://openrootdev.github.io/vipermesh-blender/setup/index.md)
- [Configuration client](https://github.com/OpenRootdev/vipermesh-blender/blob/main/docs/client-setup.md)
- [Bundles de version](https://github.com/OpenRootdev/vipermesh-blender/releases)
- [Manuel du connecteur](https://github.com/OpenRootdev/vipermesh-blender/blob/main/docs/portable-blender-mcp.md)
- [Compétence d'agent](https://github.com/OpenRootdev/vipermesh-blender/blob/main/skills/using-vipermesh-blender/SKILL.md)
- [Limite de sécurité](https://github.com/OpenRootdev/vipermesh-blender/blob/main/SECURITY.md)
- [Présentation illustrée](https://openrootdev.github.io/vipermesh-blender/#overview)
- [Harness Library](https://openrootdev.github.io/harness-library/harnesses/vipermesh-blender/)
