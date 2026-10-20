<a id="mcp-client-setup"></a>
# Configuration du client MCP

<a id="what-starts-what"></a>
## Qui démarre quoi

ViperMesh for Blender possède deux connexions locales :

1. Un client MCP démarre le serveur Node ViperMesh comme sous-processus stdio de
   longue durée.
2. Le serveur Node ouvre et réutilise une connexion TCP sérialisée vers l'addon
   Blender sur `127.0.0.1:9876`.

Le client MCP est responsable du cycle de vie du serveur. Enregistrez le serveur
une seule fois dans le client, puis utilisez les outils MCP exposés dans cette
session client. Exécuter une commande `npm`, `npx` ou `tsx` séparée pour chaque
appel d'outil crée un nouveau processus serveur et abandonne la connexion
persistante.

Docker n'est pas requis pour les clients qui prennent en charge les serveurs MCP
stdio locaux.

<a id="native-stdio-setup"></a>
## Configuration stdio native

Clonez, installez et construisez le dépôt :

```bash
git clone https://github.com/OpenRootdev/vipermesh-blender.git
cd vipermesh-blender
npm install
npm run build
```

Utilisez le point d'entrée construit depuis un chemin absolu. Cela évite de
dépendre d'une option de répertoire de travail propre à un client.

<a id="codex"></a>
### Codex

```bash
codex mcp add vipermesh-blender -- node C:/absolute/path/to/vipermesh-blender/dist/public-portable-blender-mcp.js
```

Confirmez l'enregistrement :

```bash
codex mcp list
```

Ouvrez une nouvelle tâche Codex si la tâche actuelle ne recharge pas les
enregistrements MCP.

<a id="json-configured-clients"></a>
### Clients configurés par JSON

Les clients comme Claude Desktop et d'autres hôtes acceptent couramment une
commande et un tableau d'arguments :

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

Le nom du fichier de configuration et la clé de premier niveau varient selon le
client. Utilisez la documentation MCP actuelle du client, mais gardez la
commande elle-même équivalente.

<a id="client-compatibility"></a>
## Compatibilité client

Un client peut utiliser cette version directement quand il prend en charge les
serveurs MCP locaux sur stdio et peut lancer un sous-processus. La prise en
charge de MCP seule ne garantit pas que :

- certains clients prennent en charge stdio local et Streamable HTTP distant ;
- certains ne prennent en charge que les URL de serveur distant ;
- certains exigent un plugin, une extension ou une politique administrateur
  avant d'autoriser l'exécution de processus locaux.

Cette version est uniquement stdio. Un client uniquement distant a besoin d'un
transport MCP hébergé séparément ou d'une passerelle compatible ; il ne peut pas
se connecter directement au protocole TCP de l'addon Blender.

<a id="docker-mcp-toolkit"></a>
## Docker MCP Toolkit

Docker MCP Toolkit peut centraliser des serveurs MCP conteneurisés et connecter
sa passerelle stdio aux clients pris en charge. C'est une route de distribution
optionnelle, pas une exigence pour ViperMesh.

ViperMesh ne publie actuellement pas d'entrée Docker MCP Catalog. L'addon
Blender reste aussi limité au loopback pour la sécurité locale. Un conteneur
doit atteindre ce service loopback hôte de manière fiable, ce qui varie selon
l'hôte Docker, le mode réseau et l'environnement client.

Pour cette raison, stdio natif est la configuration prise en charge aujourd'hui.
N'exposez pas le pont Blender sur une interface publique simplement pour
permettre à un conteneur de se connecter. Les instructions Docker Toolkit seront
promues en chemin pris en charge après qu'un test de connectivité bout à bout
Windows, macOS et Linux aura défini une configuration sécurisée.

Références officielles :

- [Transports MCP](https://modelcontextprotocol.io/specification/latest/basic/transports)
- [Docker MCP Toolkit](https://docs.docker.com/ai/mcp-catalog-and-toolkit/)

<a id="verify-the-session"></a>
## Vérifier la session

1. Démarrez Blender et le pont local ViperMesh.
2. Ouvrez une nouvelle session dans le client MCP configuré.
3. Appelez `bootstrap_vipermesh_session`.
4. Confirmez que `connection.connected` vaut `true` et que `sessionModel` vaut
   `persistent`.
5. Effectuez deux appels d'inspection légers. Ils doivent réutiliser un seul
   processus MCP et un seul client Blender plutôt que de démarrer de nouvelles
   commandes shell.
