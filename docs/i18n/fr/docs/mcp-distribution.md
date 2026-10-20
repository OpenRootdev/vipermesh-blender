<a id="mcp-distribution"></a>
# Distribution MCP

ViperMesh for Blender est publié comme connecteur stdio local. Il n'héberge pas
Blender, ne fournit pas de modèle IA et n'inclut pas ViperMesh Studio privé ni
son harnais complet benchmarké.

<a id="published-listings"></a>
## Listes publiées

- [Smithery : ker102/vipermesh-blender](https://smithery.ai/servers/ker102/vipermesh-blender)
- [Registre MCP officiel : io.github.Ker102/vipermesh-blender](https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.Ker102/vipermesh-blender)
- [Version GitHub v1.3.0](https://github.com/OpenRootdev/vipermesh-blender/releases/tag/v1.3.0)

Le registre officiel héberge les métadonnées. Le package MCPB est hébergé dans
la version GitHub. La liste Smithery contient aussi le même bundle et les neuf
schémas d'outils MCP découverts depuis le serveur packagé.

<a id="bundle-setup"></a>
## Configuration du bundle

1. Installez et activez l'addon Blender avec le [guide d'installation principal](../README.md#install).
2. Téléchargez [vipermesh-blender-1.3.0.mcpb](https://github.com/OpenRootdev/vipermesh-blender/releases/download/v1.3.0/vipermesh-blender-1.3.0.mcpb)
   et son [fichier SHA-256](https://github.com/OpenRootdev/vipermesh-blender/releases/download/v1.3.0/vipermesh-blender-1.3.0.mcpb.sha256).
3. Importez le bundle dans un client compatible MCPB, en suivant les
   instructions d'extension locale de ce client. Node.js est requis par la
   configuration de lancement du bundle. Gardez le port du pont à `9876` sauf si
   votre addon utilise un port différent.
4. Démarrez le pont Blender local, puis appelez `bootstrap_vipermesh_session`
   depuis le client IA et inspectez le résultat de connexion.

Les clients sans import MCPB peuvent utiliser l'[installation depuis les sources](client-setup.md).
Sinon, le MCPB est une archive ZIP : extrayez-la dans un répertoire permanent et
enregistrez `node` avec le chemin absolu vers `server/index.mjs` comme argument.
Le package extrait contient ses dépendances d'exécution et ses conseils locaux ;
aucun `npm install` n'est nécessaire. Démarrez-le une seule fois comme
sous-processus stdio persistant, pas une fois par opération Blender.

Le pont reste sur `127.0.0.1`. Les clients uniquement distants ne peuvent pas
utiliser directement ce connecteur local. N'exposez pas publiquement le pont
Blender pour les faire se connecter.

<a id="release-integrity-and-validation"></a>
## Intégrité et validation de la version

La version `1.3.0` est construite depuis le commit source
`781700be4f0fb32b135d3f5cb7da012ce8fc4abd`.

SHA-256 du bundle :

```text
45f8cee90540e9f906b8e817efb6fa0a1302f8dba515522dc3682d328a90206c
```

Les vérifications TypeScript source et de conformité, la syntaxe Python de
l'addon, la validation du schéma de package, l'initialisation MCP, la découverte
des neuf outils et les recherches de conseils locaux ont réussi. Le
téléchargement de la version a été vérifié avec cette somme de contrôle avant la
publication au registre.

Ces vérifications de package n'établissent pas la compatibilité Blender en
direct pour chaque client. Un test de scène en direct et un test d'installation
MCPB bout à bout restent en attente pour ce bundle. Testez sur une scène
jetable, examinez les opérations destructrices et suivez les [consignes de sécurité](../SECURITY.md).

<a id="maintainer-notes"></a>
## Notes pour les mainteneurs

Les métadonnées de registre publiées sont suivies dans [server.json](../../../../server.json).
Pour une nouvelle version, reconstruisez et validez le bundle, téléversez ses
octets exacts et sa somme de contrôle vers la version, puis mettez à jour
ensemble la version, le commit source, l'URL de téléchargement et le hash avant
de publier les métadonnées.

Le manifeste MCPB liste les noms d'outils. La publication Smithery nécessite en
plus les schémas complets `tools/list` du serveur packagé ; les noms seuls ne
satisfont pas la validation de sa carte serveur. Gardez ces schémas cohérents
avec la version au lieu d'inventer ou de supprimer des définitions d'outils.
