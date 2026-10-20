<a id="changelog"></a>
# Journal des modifications

Toutes les modifications notables de ViperMesh for Blender sont documentées ici.

<a id="unreleased"></a>
## [Non publié]

<a id="130---2026-10-07"></a>
## [1.3.0] - 2026-10-07

<a id="added"></a>
### Ajouté

- Présentation GitHub Pages connectée au dépôt, installation et limites de
  capacité honnêtes.
- Sortie PNG/JPEG bornée en ligne pour les clients MCP capables de traiter les
  images.
- Diagnostics de géométrie/déformation et opérations d'addon protégées déjà
  présents dans la surface d'outils Blender actuelle, synchronisés dans la
  distribution publique.

<a id="changed"></a>
### Modifié

- La finalisation peut préserver la caméra/l'éclairage existants et effectuer
  un rendu sans enregistrer de fichier blend. Les échecs spatiaux nommés
  bloquent la sortie finale et conservent les détails de réparation.
- Suppression des nombres d'aperçus fixes ; exige une revue visuelle fondée sur
  la tâche et signale les défauts non résolus au lieu de traiter l'état du
  fichier comme un verdict de qualité.
- Les enregistrements blend sont explicites et refusent les destinations
  existantes lors de la finalisation par étapes.
- Mise à jour du verrou de dépendances public et du plancher SDK ; l'audit
  d'installation propre est clair.
- La validation de package vérifie chaque référence de compétence livrée.
- Correction du rollback de retargeting après un échec de sauvegarde ou
  d'export, du nettoyage d'import partiel, de la gestion des opérateurs annulés,
  de la conversion des arguments enum-flag et des empreintes d'addon conscientes
  de l'implémentation. Ajout de régressions d'exécution Blender.

<a id="changed-1"></a>
### Modifié

- Remplacement du corpus privé exporté de guides d'outils par une compétence
  d'agent publique concise et installable ainsi que des documents de référence
  adaptables.
- Ajout d'une configuration client stdio native explicite et clarification de la
  route Docker MCP Toolkit optionnelle, pas encore prise en charge.
- Ajout de vérifications d'export qui empêchent le contenu privé
  `data/tool-guides` d'entrer dans les versions publiques.

<a id="120---2026-07-25"></a>
## [1.2.0] - 2026-07-25

<a id="added-1"></a>
### Ajouté

- Serveur MCP stdio persistant avec une connexion Blender sérialisée par session
  d'agent.
- Addon Blender avec états explicites Stopped, Ready, Agent connected et Error.
- Outils déterministes d'inspection de scène, d'assemblage, de matériaux,
  d'éclairage, de caméra, de rendu, d'animation, de rigging, d'UV, d'export et
  de retopologie.
- Appels batch bornés et flux de travail par étapes pour construction,
  inspection d'aperçu et finalisation.
- Bootstrap de session, ressources MCP, contexte opérationnel compact et
  conseils de tâche versionnés pour les nouveaux agents.
- Fallback explicite `execute_code` pour le travail Blender réellement
  personnalisé.
- Transport loopback local uniquement et validation de version publique.

[Non publié]: https://github.com/OpenRootdev/vipermesh-blender/compare/v1.3.0...HEAD
[1.3.0]: https://github.com/OpenRootdev/vipermesh-blender/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/OpenRootdev/vipermesh-blender/releases/tag/v1.2.0
