<a id="public-connector-release-checklist"></a>
# Checklist de publication du connecteur public

Le dépôt public est généré à partir de
`config/public-blender-connector-files.json`. Ne forkez jamais et ne copiez
jamais l'historique du dépôt privé.

<a id="current-release"></a>
## Version actuelle

- Dépôt : https://github.com/OpenRootdev/vipermesh-blender
- Cible de version : https://github.com/OpenRootdev/vipermesh-blender/releases/tag/v1.3.0
- Cible de version source : `v1.3.0`
- Cible de compatibilité Blender : 5.2
- CI : typecheck autonome, tests de conformité, build, validation de package,
  audit npm et compilation Python de l'addon
- Validation historique en direct (v1.2.0) : découverte MCP stdio persistante,
  appels de scène, mutation, aperçu/finalisation par étapes, enregistrement,
  conseils locaux et fallback `execute_code`
- Vérifications de lancement actuelles : conformité de package isolée,
  transport d'images en ligne, étapes de rendu seul/présentation préservée,
  rétention en cas d'échec spatial, audit de dépendances, compilation Python et
  revue du site desktop/mobile. La performance complète d'agent en direct est
  évaluée dans le prochain pilote de démo.

<a id="before-export"></a>
## Avant export

- Exécuter `npm run validate:public-blender-connector`.
- Exécuter la passerelle MCP portable et les tests centrés sur l'UI de l'addon.
- Compiler l'addon avec `python -m py_compile`.
- Installer l'addon généré dans la version actuelle Blender 5.2.
- Vérifier les états UI Stopped, Ready, Agent connected et Error.
- Vérifier bootstrap, inspection de scène, une mutation, inspection d'aperçu,
  rendu final, enregistrement et arrêt via un nouveau client MCP.

<a id="export-safety"></a>
## Sécurité d'export

- Exporter uniquement les entrées du manifeste.
- Rejeter les cibles dupliquées, fichiers manquants, chemins absolus,
  traversées, chemins d'application privés, secrets, identifiants, preuves de
  benchmark internes et code de fournisseur propre à un concurrent.
- Scanner à nouveau le répertoire généré avant de créer le dépôt GitHub.
- Créer `Ker102/vipermesh-blender` comme nouveau dépôt sans commits privés
  hérités.

<a id="release"></a>
## Publication

1. Installer les dépendances et exécuter `npm run check` dans le répertoire
   généré.
2. Packager l'addon comme artefact de version.
3. Taguer la version du connecteur.
4. Publier le package MCP seulement après inspection de son contenu.
5. Épingler le produit ViperMesh privé à la version publiée du connecteur.
6. Vérifier le chemin d'installation public indépendamment.
7. Alors seulement, changer la visibilité du dépôt du produit ViperMesh.
