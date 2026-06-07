# Plan / Feuille de route — EDGE

Légende : ✅ fait · 🔄 en cours · ⬜ à faire

EDGE = plateforme de **conseil/analyse** de paris pour Mise-o-jeu (Loto-Québec).
On ne parie pas dans l'app : on analyse, on conseille, on suit la performance.

---

## ✅ Déjà fait

### Moteur (statistique, auditable)
- ✅ Client API-Football (**PRO**) + cache disque + anti rate-limit
- ✅ Moteur **Poisson** (1X2, Over/Under 2.5, BTTS, double chance)
- ✅ Stats équipes → buts attendus — mode **club** ET mode **équipes nationales** (CDM)
- ✅ Détection des **value bets** + génération de **combinés** (cote ~3.00)
- ✅ **Validateur Mise-o-jeu** (liste blanche) → jamais de match injouable
- ✅ Scan **automatique** multi-dates (un seul bouton)
- ✅ Cotes consensus (~13 bookmakers, dont Pinnacle)

### Application (Next.js + FastAPI)
- ✅ App **EDGE** « Find the Value » — design Apex Velocity (glassmorphism)
- ✅ Pages : Accueil (hero + snapshot) · Générer · Analyses · Performance · Historique
- ✅ Page **match détaillée** : conseil de paris, barre 1X2, forme, tous les marchés
- ✅ **Classement par groupe** (CDM = groupes séparés) avec les 2 équipes surlignées
- ✅ **Pronostic croisé** : nos probas EDGE vs API-Football
- ✅ **Heures en heure de l'Est (Canada / Québec)**
- ✅ Persistance des **tickets** (SQLite) + suivi gagné/perdu manuel
- ✅ **Analytics** : ROI, taux de réussite, profit

### Cerveau IA (DeepSeek)
- ✅ Analyste **DeepSeek (reasoner)** : raisonne sur un dossier (Poisson + forme +
  blessures + H2H + classement + pronostic API) → analyse fine + conseil nuancé
- ✅ **Cache permanent** des analyses IA + bouton « Rafraîchir »
- ✅ Règle absolue : le LLM **ne calcule jamais** les probas (Poisson = vérité)

---

## ⬜ Prochaines pistes (par valeur)

| Piste | Valeur | Effort | Statut |
|-------|--------|--------|--------|
| 🎯 **Backtest** — rejouer le modèle sur les saisons passées, mesurer le ROI réel | ⭐⭐⭐ *décisif avant de vendre* | élevé | ⬜ |
| ✅ **Vérif. auto des résultats** — actualiser un ticket et voir tout seul s'il a gagné | ⭐⭐⭐ | moyen | ⬜ |
| 🌗 **Light mode** — thème clair en plus du sombre (toggle) | ⭐⭐ | faible | ⬜ |
| 🤖 **IA sur les combinés** — analyse globale d'un ticket entier | ⭐⭐ | moyen | ⬜ |
| 📊 **Page Équipe dédiée** — historique complet + stats d'une équipe | ⭐⭐ | moyen | ⬜ |
| 🩹 **Blessures + H2H affichés** sur la page match (déjà récupérés pour le LLM) | ⭐ | faible | ⬜ |

### 🎯 Backtest (LA priorité)
- ⬜ Rejouer le modèle sur les saisons passées (matchs terminés)
- ⬜ Comparer la prédiction au résultat réel
- ⬜ Mesurer **ROI / yield / taux de réussite** des combinés
- ⬜ Vérifier que le modèle bat la clôture du marché
- ⬜ Ne vendre aux clients QUE si rentable sur 1000+ matchs

### ✅ Vérification automatique des résultats (auto-settlement)
- ⬜ Pour chaque ticket sauvegardé, récupérer le **résultat réel** des matchs (API-Football)
- ⬜ **Grader** chaque sélection (gagnée / perdue) selon le marché (1X2, O/U, BTTS, DC)
- ⬜ Marquer le ticket **gagné/perdu automatiquement** (combiné = toutes gagnantes)
- ⬜ Bouton « Actualiser les résultats » + statut « en attente » tant que le match n'est pas joué
- ⬜ Alimente l'Analytics (ROI réel) sans saisie manuelle

### 🌗 Light mode
- ⬜ Thème clair (variables de couleur alternatives)
- ⬜ Toggle dans la barre du haut, préférence mémorisée (localStorage)

---

## Phase produit (plus tard)
- ⬜ Comptes utilisateurs + abonnement (freemium / mensuel)
- ⬜ Migration SQLite → PostgreSQL
- ⬜ Gestion de bankroll (critère de Kelly fractionnel)
- ⬜ Jeu responsable + conformité (Québec / Loto-Québec)
- ⬜ Historique public vérifiable (gagnés ET perdus) pour la confiance

---

## Règle d'or
Un combiné cote 3.00 ≈ 33 % de proba théorique. L'avantage ne vient pas de
« prédire le gagnant » mais de trouver les **erreurs de cote** (value).
**Prouver la rentabilité en backtest avant de vendre quoi que ce soit.**
