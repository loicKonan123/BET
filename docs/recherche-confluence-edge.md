# EDGE : recherche sur la confluence et refonte de l'analyse

Recherche du 7 septembre 2026. Les priorités ci-dessous sont des recommandations
pour ce dépôt, fondées sur l'examen du code et sur les sources citées. Elles ne
constituent pas des gains de performance déjà mesurés sur EDGE.

## Ce que possède déjà l'application

Le consensus combine Poisson/Dixon-Coles ajusté, Elo, probabilités de marché
après retrait de marge, et un gradient boosting enrichi en xG lorsqu'un modèle
est disponible pour la ligue. Ajouter « un modèle xG » sans regarder l'existant
ferait donc doublon. Le ML utilise notamment l'Elo et les buts passés : les
quatre sources ne sont pas indépendantes.

Les poids actuels sont conservés. L'avis probabiliste du LLM conserve également
sa fusion existante avec le consensus (55 % consensus / 45 % avis IA dans le
pool logarithmique). Cette pondération n'est pas validée par cette recherche.
Un texte convaincant ne constitue pas une preuve de calibration.

## Modèles à comparer, dans l'ordre proposé

| Priorité | Candidat | Apport recherché | Données nécessaires | Décision proposée |
|---|---|---|---|---|
| 1 | Poisson bayésien hiérarchique | Partage d'information entre équipes et incertitude sur leurs forces | Scores à 90 minutes, dates, équipes, terrain et saisons | Comparer à Dixon-Coles, particulièrement sur petits échantillons et promus |
| 2 | Poisson bivarié dynamique | Forces offensives/défensives évolutives et dépendance entre scores | Historique chronologique suffisamment dense | Challenger du modèle de buts existant, avant ajout d'un vote supplémentaire |
| 3 | Modèle de résultat enrichi par les joueurs | Effet des compositions et des absences documentées | Minutes, titulaires, remplaçants, événements et disponibilité avant match | À différer tant que la couverture historique est insuffisante |
| 4 | Glicko-2 adapté au football | Incertitude de classement et volatilité, au-delà d'un Elo ponctuel | Résultats datés, inactivité, terrain, traitement explicite du nul | Challenger d'Elo ; pas un 1X2 prêt à brancher |
| 5 | Méta-modèle calibré de fusion | Apprendre quand chaque source est utile | Prévisions de chaque modèle produites hors entraînement, résultats, disponibilité des sources | Comparer au pool actuel sur les mêmes matchs |

### 1. Bayésien hiérarchique

Le modèle de Baio et Blangiardo formalise une approche hiérarchique des résultats
de football. Pour EDGE, l'intérêt serait de partager l'information entre équipes
et de représenter l'incertitude des paramètres, plutôt que d'afficher uniquement
une estimation ponctuelle. Il faut aussi contrôler la régularisation excessive
des équipes extrêmes. C'est une piste d'implémentation à comparer, pas un modèle
déjà ajouté. [Baio et Blangiardo, publication et dépôt universitaire](https://www.boa.unimib.it/handle/10281/4811).

Contrat proposé : probabilités 1X2 et marchés de buts, distribution prédictive
des scores, date limite des observations, effectifs d'échantillon et diagnostics
d'ajustement. Les intervalles sur les paramètres ne doivent pas être confondus
avec une garantie sur le score final. Prévoir un apprentissage hors requête web.

### 2. Poisson bivarié dynamique

Koopman et Lit modélisent des intensités de buts qui évoluent dans le temps dans
un cadre de séries temporelles, avec dépendance entre scores. Pour EDGE, ce
candidat pourrait mieux suivre les changements de force qu'un ajustement global
avec simple pondération temporelle. Cela reste une hypothèse à tester. Leur
évaluation historique ne démontre pas une rentabilité actuelle pour nos ligues.
[Prépublication des auteurs, 2012](https://research.vu.nl/ws/files/3167073/12099.pdf),
[article publié en 2015](https://rss.onlinelibrary.wiley.com/doi/10.1111/rssa.12042).

Les deux modèles de buts partageraient les scores d'entrée. Comparer d'abord
le remplacement de Dixon-Coles, puis un mélange plafonnant le poids global de
cette famille ; ne pas traiter leur proximité comme deux confirmations autonomes.

### 3. Joueurs et qualité des occasions

Whitaker et ses coauteurs proposent d'inférer des capacités de joueurs et de
les intégrer à un modèle hiérarchique de résultats. Cela ouvre une piste plus
documentée que « un attaquant absent vaut moins 10 % ». L'application aurait
besoin d'historiques de compositions et de minutes disponibles au bon instant.
[Article des auteurs](https://arxiv.org/abs/1710.00001).

Les xG observés évaluent la qualité des tirs à partir de leur contexte ; ils ne
sont pas équivalents aux buts attendus produits par Poisson. Le fournisseur et
la couverture doivent être conservés dans le dataset. Améliorer les entrées du
ML existant serait une évolution, pas une nouvelle source indépendante.
[Définition et variables chez StatsBomb](https://statsbomb.com/soccer-metrics/expected-goals-xg-explained/).

### 4. Glicko-2

Glicko-2 ajoute au classement une déviation et une volatilité. Son intérêt
potentiel est d'éviter de traiter de la même manière une équipe bien observée
et une équipe peu active. Il ne fournit pas directement les trois probabilités
football domicile/nul/extérieur : une couche de résultat et un avantage terrain
doivent être estimés puis validés. [Spécification de Mark Glickman](https://www.glicko.net/glicko/glicko2.pdf).

Tester d'abord Glicko-2 contre Elo, puis leur contribution marginale. Le risque
principal pour EDGE serait de compter deux fois presque le même signal de force.

### 5. Fusion et calibration

Un méta-modèle peut apprendre à combiner les sorties des sources. Les prévisions
qui l'entraînent doivent provenir de modèles qui n'ont pas vu le résultat à
prédire. Utiliser les sorties d'entraînement des modèles de base expose à un
surapprentissage. [Documentation officielle du stacking](https://scikit-learn.org/dev/modules/generated/sklearn.ensemble.StackingClassifier.html).

Construire manuellement des prévisions par blocs chronologiques ; le découpage
par défaut d'un classificateur de stacking n'est pas un protocole temporel.
Les matchs simultanés restent dans le même bloc. La calibration doit disposer
de données distinctes de celles ayant servi à ajuster le modèle.
[Découpage temporel](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html),
[calibration des probabilités](https://scikit-learn.org/stable/modules/calibration.html).

## Conditions avant activation d'une nouvelle source

1. Stocker une photographie pré-match : heure des données, cotes réellement
   disponibles, version des modèles et probabilités. Une cote courante ne
   devient pas une cote de clôture par simple renommage.
2. Rejouer les saisons dans l'ordre : apprentissage, choix des paramètres,
   calibration, puis test final sur des dates ultérieures. Aucun résultat futur,
   classement final ou composition publiée après l'instant étudié en entrée.
3. Comparer chaque candidat au consensus actuel sur les mêmes rencontres, ainsi
   qu'au marché lorsqu'il existe. Rapporter aussi les matchs non couverts.
4. Mesurer log-loss, Brier et courbes de fiabilité, par ligue et globalement.
   Le RPS peut compléter le rapport, mais son usage pour le football est discuté ;
   ne pas sélectionner un modèle sur cette seule mesure.
   [Wheatcroft, discussion du RPS](https://arxiv.org/abs/1908.08980).
5. Quantifier l'incertitude des écarts par rééchantillonnage de blocs temporels,
   et tester le retrait de chaque source. Privilégier un apport répété sur
   plusieurs périodes à une amélioration isolée après de nombreux essais.
6. Évaluer rendement et évolution des cotes uniquement avec des prix archivés
   exploitables. Sans cet historique, conclure sur la prévision probabiliste,
   pas sur une rentabilité supposée.

Limite repérée dans le dépôt : les caches de modèles de production ne sont pas
tous indexés par la date du match. Les statistiques et classements disponibles
aujourd'hui ne reconstruisent pas automatiquement un état historique. Le filtre
sur les derniers matchs ajouté à l'analyse ne résout pas à lui seul ce problème.
Ne pas utiliser la page d'un ancien match comme preuve de performance pré-match.

## Changements livrés dans cette révision

- Désaccord mesuré sur les trois issues, exclusion de sources probabilistes
  invalides, diagnostic de sensibilité lorsqu'on retire chaque source.
- Une source unique n'affiche plus une convergence entre modèles.
- Dossier IA enrichi des compositions, derniers matchs et H2H antérieurs au
  match ; indication de couverture des blessures et repères de prix calculés.
- Une synthèse suivie de sept sections rédigées : rapport de force, duel,
  confrontation des modèles, scénario contraire, prix, risques et verdict.
- Consignes explicites pour distinguer fait, hypothèse et donnée absente.
  Le contrôle automatique valide la structure et les probabilités, pas la
  véracité de chaque phrase : la qualité éditoriale reste à vérifier sur des
  générations réelles.
- Affichage en colonne de lecture, contrat TypeScript complété, JSON validé
  avant cache, version du format et rejet des réponses tronquées.

Les cinq candidats ci-dessus sont étudiés et priorisés ; aucun nouveau modèle
prédictif n'est activé dans cette révision. Les diagnostics de confluence ne
sont pas présentés comme des modèles supplémentaires.

## Mise en route et validation

Redémarrer le backend puis demander une analyse sur une fiche match. Les anciens
caches ne satisfont plus la version éditoriale ; l'ouverture de la fiche reste
sans appel LLM et une nouvelle analyse est produite à la demande.

Le mode par défaut est désormais `DEEPSEEK_ANALYSIS_MODE=rapide` : rédaction
directe avec `thinking` désactivé, plafond de 8 192 tokens et un seul appel,
sans reprise automatique du SDK ni seconde génération après troncature. Les
anciens alias `deepseek-reasoner` et `deepseek-chat` sont remplacés par
`deepseek-v4-flash` dans ce mode. Le timeout réseau du client est de 60 secondes ;
il ne constitue pas une limite globale couvrant la collecte du dossier.

Le mode optionnel `approfondi` conserve le modèle configuré, le budget par
défaut de 32 768 tokens et au plus une nouvelle génération après troncature,
jusqu'à 65 536 tokens. `DEEPSEEK_MAX_TOKENS` définit le budget initial ; le mode
rapide le plafonne à 8 192. Les sept sections éditoriales sont conservées dans
les deux modes. Le délai réel dépend aussi des API et des données en cache.
Le dossier complet peut ajouter des appels
API pour les derniers matchs et compositions. Le mode JSON et la détection de
troncature suivent la [documentation DeepSeek](https://api-docs.deepseek.com/guides/json_mode/).

Vérifications locales : `python -m unittest discover -s tests -v` depuis
`backend`, et `node node_modules/typescript/bin/tsc --noEmit --incremental false`
depuis `frontend`. Les tests simulent le fournisseur IA et ne mesurent donc ni
la qualité réelle de rédaction ni la précision des prédictions.
