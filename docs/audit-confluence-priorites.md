# EDGE — audit approfondi et choix du prochain modèle

7 septembre 2026. Recherche et audit en lecture seule du moteur : aucun poids,
modèle ni comportement de production modifié pour cette étude.

## Avis et décision

EDGE possède une architecture intéressante pour l'analyse de football : moteur
de scores, classement Elo, signal xG, marché et rédaction explicative. La
précision et la rentabilité du système complet restent à établir sur un test
chronologique distinct de la sélection des modèles. Une amélioration du texte
ou un temps de réponse réduit n'est pas une validation prédictive.

Ma priorité est : fiabiliser données et calibration, mesurer les contributions,
puis comparer un modèle contextuel au consensus existant. Un Poisson dynamique
constitue le prochain challenger de la famille des modèles de buts.

Cette priorité affine le premier rapport : le Dixon-Coles existant possède déjà
une régularisation L2 et une décroissance temporelle. L'intérêt d'un modèle
bayésien serait surtout l'incertitude explicite et l'évolution des paramètres,
pas simplement l'ajout d'une régularisation que nous avons déjà.

## Constats vérifiables dans le dépôt

| Constat | Localisation | Conséquence |
|---|---|---|
| Elo est converti en buts attendus, puis en 1X2 avec `compute_probabilities` | `backend/src/elo.py`, `proba_1x2_elo` | Elo et Dixon-Coles partagent une hypothèse de distribution ; leur accord ne représente pas deux preuves indépendantes |
| Le gradient boosting utilise Elo, buts glissants et xG | `backend/src/ml.py`, `FEATURES` | Un deuxième gradient boosting avec les mêmes entrées apporterait surtout une variante d'algorithme |
| Le calibrateur isotonique utilise `cv=3` | `backend/src/ml.py`, entraînement et évaluation | Les plis internes ne sont pas chronologiques ; refaire la calibration sur des dates postérieures à l'apprentissage |
| Le ML est admissible dès 200 observations | `backend/src/ml.py`, `min_lignes` | Les ensembles internes de calibration peuvent être petits pour l'isotonique |
| Le test ML externe est une séparation chronologique unique | `backend/src/ml.py`, `evaluer_ml` | C'est une protection utile, mais pas une validation sur plusieurs fenêtres indépendantes |
| Les séries xG ne sont mises à jour que lorsque les deux équipes ont une valeur | `backend/src/ml.py`, `_rejouer` | Six observations xG peuvent couvrir plus de six matchs ; mesurer leur âge et la couverture |
| Les entraînements acceptent FT, AET et PEN et lisent `goals` | `ml.py`, `elo.py`, `dixon_coles_fit.py` | Vérifier les scores à 90 minutes pour éviter des cibles incompatibles avec les marchés 1X2 usuels |
| `rho` est un paramètre fixé par défaut, non estimé dans le vecteur optimisé | `backend/src/dixon_coles_fit.py`, `ajuster` | Tester son estimation ou son réglage temporel avant de remplacer tout le modèle |
| Les cotes sont mises en cache sans TTL dans cet appel | `backend/src/odds_parser.py`, `recuperer_cotes` | L'heure de validité et les changements de prix doivent être suivis |
| Les cotes moyennes servent de prix de référence | `backend/src/odds_parser.py` | Une cote moyenne n'est pas nécessairement un prix auquel l'utilisateur peut réellement parier |
| La fusion donne 55 % au consensus et 45 % à l'avis IA | `backend/src/analyste.py`, `_fusion_equipe` | Évaluer séparément le consensus seul et le verdict enrichi ; aucune justification nouvelle du poids 45 % n'a été établie |

La documentation officielle confirme que `cv` entier utilise des plis
stratifiés pour une classification, et déconseille l'isotonique lorsque les
échantillons de calibration sont très inférieurs à 1 000. Cela ne prouve pas
que le test externe actuel est contaminé : cela montre que l'apprentissage
interne ne reproduit pas une calibration prospective.
[CalibratedClassifierCV](https://scikit-learn.org/stable/modules/generated/sklearn.calibration.CalibratedClassifierCV.html).

## Ce que la recherche change dans le choix des candidats

Inventaire local effectué pendant l'audit, après déduplication des fixtures par
identifiant dans `backend/data/cache/fixtures_league-*.json` : 24 894 matchs,
dont 20 528 terminés, répartis sur 38 ligues parmi les matchs terminés. Parmi
315 rencontres AET/PEN, toutes ont un score `fulltime` complet ; 100 scores
globaux diffèrent du score à 90 minutes et 76 changent même l'issue 1X2.
Ces nombres mesurent le contenu du cache, pas le nombre exact de lignes utilisées
dans chaque modèle. C'est une preuve concrète du risque de cible incompatible.

Le cache comporte aussi 3 512 fichiers `fixtures_statistics_fixture-*.json`,
dont 3 503 avec un champ `expected_goals` non nul pour les deux équipes, ainsi
que cinq fichiers de modèles ML sur disque. Ces décomptes n'attestent ni de la
fraîcheur, ni de la validité numérique de chaque xG, ni de la couverture uniforme
par ligue. Les fichiers statistiques ne sont pas nécessairement tous inclus
dans le sous-ensemble de fixtures précédent : ne pas en déduire un pourcentage
global de couverture sans jointure et contrôle des dates.

**1. Modèle contextuel : mon premier candidat pour une information nouvelle.**
Construire une régression multinomiale régularisée de référence, puis comparer
un gradient boosting avec les mêmes entrées : repos depuis le match précédent,
charge de matchs sur 7/14 jours, continuité du onze, absences documentées,
minutes des joueurs et éventuellement déplacement réel. Les entrées indisponibles
restent explicitement manquantes. Les coefficients doivent être appris ; aucun
bonus de probabilité arbitraire par blessure.

L'étude de Settembre et al. (2024) examine notamment Elo, déplacements, repos et
rotation. Les contributions du repos et de la gestion des joueurs sont plus
petites que celles des principaux facteurs dans leur analyse. Elle justifie
des variables à tester, pas un gain garanti ni un lien causal universel.
[Étude originale](https://journals.sagepub.com/doi/10.3233/JSA-240745).

Deux versions seraient nécessaires : avant publication des compositions et
après publication. Une composition réellement utilisée ne doit jamais être
introduite dans une prédiction datée d'avant son annonce. Une première version
peut démarrer avec repos et calendrier, mais l'inventaire des données doit
précéder tout développement du volet joueurs.

**2. Modèle de buts dynamique : meilleur challenger structurel.**
Comparer le Dixon-Coles actuel à des forces attaque/défense évoluant dans le
temps, avec une distribution bivariée. Koopman et Lit développent ce cadre pour
le football. Leur résultat sur des saisons anciennes ne garantit pas un avantage
dans les ligues actuelles d'EDGE. Entraîner hors ligne et charger les paramètres
en mémoire pour préserver la vitesse de consultation.
[Prépublication des auteurs, 2012, article publié en 2015](https://research.vu.nl/ws/files/3167073/12099.pdf).

Ne pas attribuer automatiquement un poids à la fois au Dixon-Coles et à son
challenger : comparer remplacement, puis combinaison au sein d'une même famille.

**3. Référence xG simple : utile pour savoir si le ML complexe mérite son coût.**
Wilkens (2026) utilise des xG récents, une distribution de Skellam et une
calibration glissante sur la Bundesliga. Le marché est généralement mieux
calibré dans l'étude ; les résultats économiques simulés varient selon les
saisons et les types de pari. La conclusion applicable à EDGE est de comparer
une référence xG explicable au gradient boosting existant, sur les mêmes dates.
[Article original](https://journals.sagepub.com/doi/10.1177/22150218261416681).

Skellam représente la différence de deux variables Poisson indépendantes : le
nom de la distribution ne crée pas à lui seul une nouvelle source d'information.
L'apport éventuel viendrait des intensités dérivées des xG et de leur validation.

**4. Fusion apprise : chantier prioritaire, mais pas nouveau capteur football.**
Apprendre des poids ou une régression de fusion à partir des prévisions hors
entraînement des sources. Comparer pool linéaire, logarithmique et méta-modèle
simple régularisé. La documentation du stacking avertit du surapprentissage
lorsque le méta-modèle apprend sur les sorties d'entraînement des modèles de
base. Il faut ici construire les observations dans l'ordre temporel.
[Documentation du stacking](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.StackingClassifier.html).

**5. Glicko-2, pi-rating, réseaux profonds et autres LLM : après ces chantiers.**
Les variantes de classement peuvent servir de challengers d'Elo, mais elles
partageront beaucoup de résultats d'entrée. Plusieurs LLM lisant le même dossier
peuvent produire une unanimité sans calibration démontrée. Je ne recommande pas
d'augmenter leur nombre dans le consensus actuel. Cette priorité est mon
appréciation d'architecture, pas un classement universel des algorithmes.

## Comment décider si un ajout mérite sa place

Conserver un historique daté de chaque prévision, avant le match : version du
modèle, données connues, source et heure de cote, marché visé, probabilités et
disponibilité des variables. Commencer sur les ligues les mieux couvertes.

Utiliser des blocs successifs d'apprentissage, calibration et test, puis avancer
dans le temps. Réserver une période finale qui ne sert ni au choix des poids,
ni au choix des seuils. Prédire tous les matchs d'un même instant avant la mise
à jour à partir des résultats. Comparer sur le même sous-ensemble couvert et
publier les exclusions.

Mesurer log-loss, Brier, courbes de fiabilité, couverture et coût de prédiction.
Le rendement nécessite des prix réellement disponibles et une règle de pari
fixée avant le test. Walsh et Joshi soulignent l'intérêt de la calibration pour
la sélection des modèles ; leurs expériences concernent la NBA, donc leurs
rendements ne sont pas transposables au football.
[Recherche originale, version 2024](https://arxiv.org/abs/2303.06021).

Exiger une amélioration reproductible sur plusieurs périodes et quantifier
l'incertitude des différences par blocs temporels. Winkelmann et al. étudient
14 saisons et montrent que des inefficiences apparentes sur une saison peuvent
ne pas persister. Une série gagnante ne suffit donc pas à valider une nouvelle
source. [Article publié dans le volume 2024](https://journals.sagepub.com/doi/10.1177/15270025231204997).

Expériences minimales : consensus actuel seul ; consensus avec calibration
temporelle ; consensus + contexte ; modèle de buts remplacé ; consensus + IA.
Chaque variante est comparée au marché seul lorsque les prix horodatés existent.
Le LLM peut continuer à expliquer les signaux pendant que son apport numérique
est testé séparément, sans nouvelle génération à chaque prédiction statistique.

## Séquence de travail recommandée

1. Corriger la définition des scores d'entraînement, contrôler la fraîcheur des
   cotes et mesurer la couverture xG. Séparer explicitement avant-match et live.
2. Refaire calibration et validation temporelles ; évaluer le poids du LLM.
3. Tester le modèle contextuel sur une ou deux ligues bien couvertes, en mode
   observation : journaliser ses sorties sans modifier les tickets.
4. Comparer le modèle dynamique de buts et la référence xG simple.
5. Apprendre la fusion uniquement si les nouveaux signaux améliorent les
   prévisions hors entraînement. Sinon conserver la version plus simple.

Le changement de modèle peut rester compatible avec une application rapide :
apprentissage planifié, modèles chargés en mémoire, données fraîches mises en
cache et rédaction IA à la demande. Aucun délai chiffré supplémentaire n'est
promis sans mesure sur l'implémentation.
