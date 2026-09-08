# Moteur EDGE commun — 8 septembre 2026

`src/prediction_service.py` est le point d'entrée des prédictions. La liste Analyses, la fiche match, les tickets ordinaires et premium, le constructeur manuel et le rédacteur IA partagent ses probabilités. Le backtest appelle sa variante locale `predire_historique`.

## Sources et cohérence

- Dixon-Coles, Elo, Poisson bivarié dynamique, régression contextuelle (repos, charge du calendrier), gradient boosting et référence xG récente.
- Les sorties 1X2, doubles chances, totaux 1,5/2,5 et BTTS proviennent d'une même distribution de scores, alignée sur le consensus 1X2. Les arrondis du 1X2 totalisent un.
- L'IA rédige l'explication ; son ancienne contribution numérique de 45 % est supprimée. Le contrat éditorial passe en version 4. Les anciens articles sont invalidés ; les articles affichés doivent avoir le même instantané ou exactement le même verdict numérique que la fiche.
- Les sélections sauvegardées sont recalculées côté serveur ; les probabilités envoyées par le navigateur ne font pas autorité. Les matchs commencés et les doublons dans un ticket sont refusés. Les anciens tickets conservés en base ne sont pas réécrits.
- Les prix proviennent d'un opérateur identifié, avec rafraîchissement à cinq minutes. Les cotes moyennes entre opérateurs ne sont plus présentées comme des prix disponibles. Une sélection automatique exige une cote valide.

## Chronologie et validation

Les apprentissages utilisent le score à 90 minutes. Les scores AET/PEN sans `score.fulltime` exploitable sont exclus. Un délai conservateur de trois heures après le coup d'envoi sépare un résultat de sa disponibilité dans l'historique.

L'entraînement sépare quatre blocs chronologiques : apprentissage, calibration par température, ajustement des poids, puis validation du déploiement. Les résultats trop proches des frontières sont exclus des blocs précédents. La fusion doit améliorer le log-loss de la référence dans les deux moitiés de la période finale pour être retenue. Cette sélection sur la période finale nécessite une confirmation prospective : ce n'est pas une mesure indépendante de la performance future de la version sélectionnée.

La passe locale finale contient 28 modèles de compétitions de clubs et un modèle partagé entre les compétitions internationales. La fusion enrichie est retenue pour 11 compétitions de clubs ; la référence est conservée pour les 17 autres et pour le pool international. Les périodes finales totalisent 4 123 matchs en comptant le pool international une seule fois. Les détails sont dans `backend/data/prediction_models/rapport_validation.json` et la page **Étude du modèle**. Les entrées internationales du rapport partagent leur validation : elles ne constituent pas des tests indépendants.

Le marché conserve un poids explicite de 50 % lorsqu'un triplet de cotes valide existe ; ce poids n'est pas appris faute d'archives suffisantes de prix datés. Les sources corrélées ne sont jamais interprétées comme des votes indépendants. La probabilité d'un combiné reste le produit des probabilités de ses matchs, sous hypothèse d'indépendance entre ces matchs.

## Disponibilité des données

Les xG sont lus dans les caches existants. Leur fenêtre avance à chaque match, y compris lorsqu'une mesure manque, et exclut les observations âgées de plus de 90 jours. La source xG simple exige une couverture minimale et n'obtient un poids appris que si les blocs nécessaires sont couverts.

Les compositions et absences présentes dans les caches peuvent être archivées avec leur date d'observation dans `backend/data/prediction_context`. Une donnée collectée après le coup d'envoi ne sert pas à prédire ce match. Une liste de blessures vide ne devient pas un effectif « au complet ». Les variables sans historique daté suffisant restent manquantes : leur présence dans le code ne signifie pas que leur effet a été appris.

Le modèle dynamique est une approximation adaptative par résidus, pas une reproduction complète d'un modèle bayésien en espace d'état. Les pronostics produits pour des matchs déjà commencés sont des reconstructions d'avant-match, pas des prévisions en direct. Les archives statistiques peuvent avoir été révisées par le fournisseur ; le suivi prospectif sert à évaluer les instantanés effectivement produits.

## Exploitation

Depuis `backend` :

```powershell
python entrainer_predictions.py --all
python entrainer_predictions.py --leagues 39 61 78
python -m unittest discover -s tests -v
python app.py
```

L'entraînement est séparé de la génération ordinaire. Les artefacts sont versionnés et remplacés atomiquement. Un artefact entraîné après la date du match est exclu. Sans artefact utilisable, la référence reste disponible si l'historique est suffisant, avec réutilisation de l'ajustement quotidien Dixon-Coles. Les compétitions internationales utilisent le même historique agrégé à l'entraînement et en production. Les saisons déjà présentes en cache sont conservées pour amorcer les forces des équipes ; les saisons récentes sont rafraîchies.

Les instantanés pré-match sont journalisés en SQLite (`predictions`). `/api/modeles/prospectif` évalue la dernière prévision antérieure au coup d'envoi lorsque le résultat à 90 minutes est disponible dans le cache. Aucun appel fournisseur supplémentaire n'est déclenché par cet audit. Les résultats inconnus sont exclus, pas comptés comme perdus ou gagnés.

Mesure locale de contrôle sur historique réel : 6,7 s au premier calcul d'une fiche entraînée, 0,4 s avec cache ; sorties identiques entre les deux parcours de la fiche et de la liste. Ces temps excluent le réseau et la rédaction IA. Les 27 tests backend et la compilation Next.js de production ont réussi. Les tests couvrent notamment la chronologie, la cohérence des marchés, les xG manquants, les poids conditionnels, l'autorité du serveur sur les tickets et l'immuabilité du journal. Le test du journal a aussi conduit à fermer explicitement les connexions SQLite pour éviter les verrous persistants sous Windows.
