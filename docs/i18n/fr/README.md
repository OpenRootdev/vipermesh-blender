<div align="center">

<!-- i18n:languages:start -->
[English](../../../README.md) | [Español](../es/README.md) | [简体中文](../zh-CN/README.md) | [Français](../fr/README.md) | [日本語](../ja/README.md) | [Deutsch](../de/README.md) | [Português (Brasil)](../pt-BR/README.md)
<!-- i18n:languages:end -->

<a href="https://openrootdev.github.io/vipermesh-blender/"><img src="../../../site/assets/brand-mark.png" alt="Logo ViperMesh" width="104" height="104"></a>

<h1>ViperMesh for Blender</h1>
<p>Serveur MCP Blender et addon open source pour agents IA.</p>

[![CI](https://github.com/OpenRootdev/vipermesh-blender/actions/workflows/ci.yml/badge.svg)](https://github.com/OpenRootdev/vipermesh-blender/actions/workflows/ci.yml)
[![GitHub release](https://img.shields.io/github/v/release/Ker102/vipermesh-blender?display_name=tag)](https://github.com/OpenRootdev/vipermesh-blender/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](../../../LICENSE)
[![MCP](https://img.shields.io/badge/Model_Context_Protocol-server-1f6feb)](https://modelcontextprotocol.io/)

**Assistance IA pour Blender, avec moins de code et moins d'attente.**

Conçu pour des modifications de scène plus rapides, moins de tokens IA et des
résultats mieux vérifiés.

<p>
<a href="https://github.com/OpenRootdev/vipermesh-blender/releases/latest"><img src="../../../site/assets/readme-download.svg" alt="Télécharger l'addon Blender" width="240" height="44"></a>
<a href="docs/client-setup.md"><img src="../../../site/assets/readme-setup.svg" alt="Guide de configuration" width="160" height="44"></a>
</p>

[Présentation du projet et configuration](https://openrootdev.github.io/vipermesh-blender/)
| [Liste d'attente ViperMesh Studio](https://vipermesh-studio.vercel.app/waitlist)

</div>

---

ViperMesh for Blender est un **serveur MCP Blender et addon** gratuit et open
source qui permet à un assistant IA compatible de travailler dans votre scène
Blender. Il s'adresse aux artistes Blender, amateurs et créateurs de jeux qui
veulent de l'aide pour créer et modifier des scènes 3D, pas un autre projet de
code.

**L'objectif : un travail assisté par IA plus rapide, moins de tokens IA et des
résultats mieux vérifiés.** Votre assistant reçoit des actions Blender prêtes à
l'emploi au lieu de devoir écrire du nouveau code Python pour de nombreuses
modifications courantes. Vous continuez à travailler dans Blender et décidez ce
que vous voulez que l'assistant vous aide à faire.

<a id="watch-the-overview"></a>
## Voir la présentation

[![Regarder la présentation de ViperMesh for Blender](../../../site/assets/connector-overview-poster.png)](https://openrootdev.github.io/vipermesh-blender/#overview)

[Regarder la vidéo de 77 secondes](https://openrootdev.github.io/vipermesh-blender/#overview)
ou [télécharger le MP4](https://openrootdev.github.io/vipermesh-blender/assets/connector-overview.mp4).
Voyez comment votre client IA utilise des actions Blender prêtes à l'emploi,
pourquoi moins de code généré peut aider, et comment commencer. C'est une
présentation illustrée avec musique, pas un enregistrement chronométré de
benchmark. Le README de GitHub renvoie vers la vidéo lisible.

<a id="why-vipermesh-for-blender"></a>
## Pourquoi ViperMesh for Blender ?

| Ce qui compte pour vous | Comment ViperMesh aide |
| --- | --- |
| Moins d'utilisation IA | Les actions réutilisables réduisent le code Blender que l'assistant doit générer pour les tâches couvertes. |
| Moins d'attente | La connexion reste ouverte, et les actions liées peuvent s'exécuter ensemble au lieu de répéter la configuration à chaque étape. |
| Scènes mieux vérifiées | Les vérifications intégrées aident à identifier les objets flottants, les mauvaises orientations et les problèmes de dégagement ; l'assistant peut inspecter les images et réparer les erreurs. |
| Plus simple pour votre assistant | Des outils découvrables et des conseils concis expliquent quelles actions sont disponibles et comment les utiliser. |
| De la place pour le travail personnalisé | L'assistant peut encore écrire du Python quand votre demande exige quelque chose que les outils prêts à l'emploi ne couvrent pas. |

Les tokens IA sont les unités de texte qu'un modèle lit et écrit. Générer moins
de code peut réduire l'utilisation IA, mais le total des tokens, le coût et le
temps dépendent aussi de votre modèle et de la tâche. Les vérifications de scène
aident à la correction ; elles ne garantissent pas un résultat beau ou sans
erreur.

<a id="one-reference-two-blender-workflows"></a>
## Une référence, deux flux Blender

<p align="center">
<a href="../../../site/assets/scandinavian-entryway-comparison.png"><img src="../../../site/assets/scandinavian-entryway-comparison.png" alt="Comparaison historique de scène : image de référence à gauche, viewport Blender MCP ViperMesh au centre et viewport BlenderMCP original à droite" width="960"></a>
</p>

Un test historique de reconstruction d'image utilisant le harnais ViperMesh
Blender MCP et les assets disponibles. Seul le titre central a été renommé ; la
référence et les deux captures de scène sont inchangées. C'est un exemple, pas
une garantie pour chaque résultat. L'addon public n'embarque pas les
bibliothèques d'assets Studio privées.

[Lire l'étude de cas Blender MCP, première partie](https://kristoferjussmann.me/case-studies/vipermesh/)
| [Ouvrir la comparaison en taille réelle](../../../site/assets/scandinavian-entryway-comparison.png)
| [Enregistrement d'intégrité d'image](../../../site/assets/scandinavian-entryway-comparison.provenance.json)

<a id="what-can-it-help-with"></a>
## Avec quoi peut-il aider ?

- Construire, déplacer, dupliquer et agencer des objets dans une scène.
- Adoucir les arêtes, ajuster les matériaux, configurer les caméras et changer
  l'éclairage.
- Vérifier si les objets reposent sur leurs supports ou laissent assez d'espace.
- Aider au nettoyage de maillage, à la retopologie, à la préparation UV, au
  rigging et aux poids.
- Travailler avec les paramètres d'animation, préparer les exports et inspecter
  les résultats.

Par exemple, vous pourriez demander à votre assistant :

> Déplace le panier sous le côté droit de la table, sans intersecter ses pieds.

> Adoucis les arêtes vives de ce meuble, en conservant sa forme générale.

> Vérifie cette scène pour trouver les objets sans support, puis montre-moi ce qui doit être corrigé.

Ce sont des exemples de demandes, pas des modèles de scène préconstruits. Vous
n'avez pas besoin d'écrire vous-même du Python Blender pour les opérations
couvertes par les outils.

<a id="how-is-it-different-from-the-original-blendermcp"></a>
## En quoi est-il différent du BlenderMCP original ?

ViperMesh s'appuie sur le
[projet BlenderMCP de Siddharth Ahuja](https://github.com/ahujasid/mcp-for-blender),
désormais nommé MCP for Blender. La différence principale est son accent sur un
large ensemble d'actions d'édition prêtes à l'emploi, de flux de travail
réutilisables et de vérifications de scène, plutôt que de dépendre de Python
nouvellement généré pour les modifications courantes.

Les deux projets peuvent inspecter des scènes et exécuter du Python
personnalisé. Le projet original offre aussi des intégrations d'assets et de
génération. L'objectif de ViperMesh est de rendre les opérations de scène
quotidiennes plus efficaces en tokens, plus rapides, plus simples à utiliser
pour les assistants et plus faciles à valider. Ce n'est pas une affirmation
qu'il gagne chaque tâche ni que le connecteur public inclut toutes les
fonctionnalités de ViperMesh Studio.

[Guide d'installation du site](https://openrootdev.github.io/vipermesh-blender/setup/) · [Liste Harness Library](https://openrootdev.github.io/harness-library/harnesses/vipermesh-blender/)

<a id="requirements"></a>
## Prérequis

- Blender 5.2 pour la cible de version actuellement testée
- Node.js 20 ou plus récent
- Un client compatible MCP qui prend en charge les serveurs stdio

MCP, abréviation de Model Context Protocol, est un standard de connexion qui
permet à un assistant IA d'utiliser des outils dans une autre application. Vous
avez besoin d'une app IA qui prend en charge ces connexions ; installer l'addon
seul n'ajoute pas de modèle IA à Blender.

<a id="install"></a>
## Installation

<a id="1-install-the-blender-addon"></a>
### 1. Installer l'addon Blender

Téléchargez l'addon `.py` versionné ou l'addon `.zip` depuis la
[dernière version](https://github.com/OpenRootdev/vipermesh-blender/releases/latest).
Dans Blender :

1. Ouvrez **Edit > Preferences > Add-ons**.
2. Choisissez **Install from Disk** et sélectionnez le fichier Python téléchargé.
3. Activez **ViperMesh for Blender**.
4. Ouvrez la barre latérale du 3D Viewport, sélectionnez **ViperMesh**, puis
   cliquez sur **Start Local Bridge**.

Gardez le pont actif pendant toute la session d'agent.

<a id="2-install-the-mcp-server"></a>
### 2. Installer le serveur MCP

**Option packagée :** Téléchargez le
[`v1.3.0` bundle MCPB](https://github.com/OpenRootdev/vipermesh-blender/releases/download/v1.3.0/vipermesh-blender-1.3.0.mcpb)
et importez-le dans un client qui prend en charge les extensions MCPB locales.
Il contient le serveur Node et ses dépendances, vous n'avez donc pas besoin de
cloner ou construire le dépôt. Node.js et l'addon Blender activé séparément
restent requis.

Le connecteur est aussi listé sur
[Smithery](https://smithery.ai/servers/ker102/vipermesh-blender) et dans le
[registre MCP officiel](https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.Ker102/vipermesh-blender).
Ces listes distribuent le connecteur local, pas un service Blender hébergé. Voir
[distribution et configuration du bundle](docs/mcp-distribution.md) pour la
somme de contrôle, l'option d'extraction manuelle et les limites actuelles de
validation.

**Option source :** Jusqu'à la publication du package npm, clonez et construisez-le :

```bash
git clone https://github.com/OpenRootdev/vipermesh-blender.git
cd vipermesh-blender
npm install
npm run build
```

<a id="3-connect-your-ai-assistant"></a>
### 3. Connecter votre assistant IA

Quand vous utilisez l'import MCPB, le client lit sa configuration de lancement
depuis le bundle. Pour l'option source, utilisez le point d'entrée construit
depuis un chemin absolu :

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

Démarrez cette commande une seule fois via le client MCP. N'invoquez pas `npm`,
`npx` ou `tsx` à nouveau pour chaque opération Blender. Voir la
[configuration du client MCP](docs/client-setup.md) pour Codex, les clients
configurés par JSON, la compatibilité et la route optionnelle Docker MCP
Toolkit.

<a id="technical-details"></a>
## Détails techniques

Les sections ci-dessous servent à configurer ou développer une connexion IA. Les
utilisateurs de Blender peuvent commencer par les étapes d'installation et les
exemples de demandes ci-dessus.

<a id="connection-model"></a>
### Modèle de connexion

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

Le serveur MCP n'ouvre aucun écouteur réseau. L'addon Blender écoute sur
loopback par défaut et affiche **Stopped**, **Ready**, **Agent connected** ou
**Error** dans la barre latérale ViperMesh.

<a id="first-agent-calls"></a>
### Premiers appels d'agent

1. Appelez `bootstrap_vipermesh_session`.
2. Inspectez la scène avec `call_blender_tool(name="get_scene_info")`.
3. Recherchez les conseils de tâche avec `search_3d_guidance`.
4. Découvrez seulement les capacités pertinentes avec `list_blender_tools`.
5. Construisez, inspectez et réparez, puis finalisez et enregistrez.

La surface MCP publique inclut :

- `bootstrap_vipermesh_session`
- `check_blender_connection`
- `list_blender_tools`
- `call_blender_tool`
- `call_blender_tool_batch`
- `run_blender_scene_stage`
- `get_blender_agent_context`
- `search_3d_guidance`
- `get_3d_guidance_document`

Lisez le [manuel complet du connecteur](docs/portable-blender-mcp.md) pour les
formes de requête, les règles de batching, les flux de travail par étapes, les
compétences d'outils locales et le dépannage. Le dépôt fournit aussi une
[compétence d'agent `using-vipermesh-blender`](skills/using-vipermesh-blender/SKILL.md)
installable.

<a id="security"></a>
## Sécurité

Ce connecteur est destiné à une station de travail locale de confiance.
`execute_code` peut exécuter du Python arbitraire dans Blender. Ne connectez que
des clients MCP de confiance, gardez le pont sur loopback et examinez les
opérations à fort impact ou destructrices.

Voir [SECURITY.md](SECURITY.md) pour la limite de confiance et le processus de
signalement privé des vulnérabilités.

<a id="public-connector-scope"></a>
## Portée du connecteur public

Ce dépôt contient l'addon Blender open source, le serveur MCP portable, les
compétences d'outils publiques portables et les tests du connecteur. Il n'inclut
pas l'application ViperMesh, l'authentification, la facturation, les prompts
privés, les données RAG privées, le routage de modèles cloud, les assets privés,
les traces brutes de benchmarks ni les jeux de données d'évaluation privés. La
comparaison illustrée est une preuve publique fournie séparément, pas une
bibliothèque d'assets embarquée.

Le connecteur n'embarque pas de fournisseur commercial de génération 3D. La
génération neuronale pourra être ajoutée plus tard via des services authentifiés
neutres vis-à-vis des fournisseurs, sans intégrer d'identifiants tiers dans
Blender.

<a id="frequently-asked-questions"></a>
## Questions fréquentes

<a id="do-i-need-a-paid-vipermesh-account"></a>
### Ai-je besoin d'un compte ViperMesh payant ?

Non. L'addon public et la connexion locale sont gratuits sans compte ViperMesh.
Votre app IA ou fournisseur de modèle peut facturer séparément. L'addon n'inclut
pas d'accès gratuit à un modèle IA.

<a id="do-i-need-to-be-a-programmer"></a>
### Dois-je être programmeur ?

Vous n'avez pas besoin d'écrire du Python pour les modifications Blender
couvertes. La configuration initiale implique tout de même d'installer l'addon
et de connecter une app IA compatible. Utilisez le bundle MCPB dans les clients
qui le prennent en charge, ou construisez depuis les sources avec les commandes
fournies. Le pont Blender activé séparément et la configuration client signifient
que ce n'est pas une installation en un clic pour tous les environnements.

<a id="does-vipermesh-replace-execute_code"></a>
### ViperMesh remplace-t-il `execute_code` ?

Non. Il réduit le Python Blender généré inutile en fournissant des opérations
structurées, mais conserve `execute_code` pour la géométrie personnalisée, les
effets procéduraux, les graphes de noeuds inhabituels et les flux de travail non
couverts.

<a id="why-must-the-mcp-process-stay-running"></a>
### Pourquoi le processus MCP doit-il rester actif ?

Le processus conserve une connexion sérialisée à Blender. Le relancer à chaque
appel ajoute un coût évitable de démarrage, de transport et d'agent-outil.

<a id="does-it-require-docker"></a>
### Docker est-il requis ?

Non. Les clients MCP locaux capables de stdio lancent directement le serveur
Node. Docker MCP Toolkit est une route optionnelle de packaging et de passerelle,
et ce n'est pas encore un chemin d'installation ViperMesh pris en charge car la
connectivité loopback hôte-vers-Blender exige encore une validation
multiplateforme.

<a id="does-the-public-connector-require-vipermesh-cloud-authentication"></a>
### Le connecteur public exige-t-il une authentification cloud ViperMesh ?

Non. L'addon public et le serveur MCP local fonctionnent sans authentification
ViperMesh. Les futurs modèles hébergés et l'orchestration propriétaire sont des
capacités produit séparées.

<a id="can-it-use-installed-blender-addons"></a>
### Peut-il utiliser les addons Blender installés ?

Le connecteur peut inspecter les addons installés et prend en charge
l'automatisation locale de confiance. Les opérations d'addons inconnues doivent
être examinées avant d'être exposées comme capacités appelables par un agent.

<a id="development"></a>
## Développement

```bash
npm install
npm run check
python -m py_compile addon/vipermesh-addon.py
```

Voir [CONTRIBUTING.md](CONTRIBUTING.md) avant d'ouvrir une pull request.

<a id="license-and-attribution"></a>
## Licence et attribution

ViperMesh for Blender est publié sous la [License MIT](../../../LICENSE). Il
inclut du travail dérivé de
[BlenderMCP](https://github.com/ahujasid/mcp-for-blender) par Siddharth Ahuja.
Voir [NOTICE.md](NOTICE.md) pour l'attribution et les avis de marque.
