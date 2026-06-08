# Plan / Feuille de route — EDGE

Légende : ✅ fait · 🔄 en cours · ⬜ à faire

EDGE = plateforme de **conseil/analyse** pour Mise-o-jeu (Loto-Québec).
On ne mise pas dans l'app : on analyse, on conseille, on suit la précision des pronostics.

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
- ✅ Pages : Accueil · Générer · Analyses · Performance · Historique · **Mon ticket**
- ✅ Page **match détaillée** : conseil de paris, barre 1X2, forme, tous les marchés
- ✅ **Marché recommandé** mis en évidence (couleur tertiary + étoile) dans le tableau
- ✅ **Classement par groupe** en tabs (un groupe à la fois, scroll interne) — groupe du match auto-sélectionné
- ✅ **Derniers matchs** avec scores réels (5 par équipe) sur la page match
- ✅ **Compositions** sur la page match (dispo ~1h avant le match)
- ✅ **Heures Montréal** (AM/PM, sans "HAE")
- ✅ Filtrage : matchs déjà joués exclus des analyses · statut EN COURS affiché
- ✅ **Light mode** — toggle, préférence mémorisée
- ✅ **Layout responsive** — max-width sur grand écran (32 pouces), centré

### Tickets & suivi
- ✅ Tickets **auto-générés** (Poisson + value bets) — sauvegarde + historique
- ✅ **Ticket builder manuel** — ajouter des sélections depuis les analyses, panier persistant (localStorage)
- ✅ **Auto-settlement** : grading automatique (score API-Football) au chargement — déclenché uniquement si heure du match + 2h passée (protection quota API)
- ✅ **Analytics** : taux de réussite, tickets gagnés/perdus/en attente (sans argent)

### Cerveau IA (DeepSeek)
- ✅ Analyste **DeepSeek (reasoner)** : raisonne sur un dossier (Poisson + forme + blessures + H2H + classement) → analyse fine + conseil nuancé
- ✅ **Cache permanent** des analyses IA
- ✅ Règle absolue : le LLM **ne calcule jamais** les probas (Poisson = vérité)

---

## ⬜ Prochaines pistes (par valeur)

| Piste | Valeur | Effort | Statut |
|-------|--------|--------|--------|
| 🎯 **Backtest** — rejouer le modèle sur les saisons passées, mesurer la précision | ⭐⭐⭐ *décisif* | élevé | ✅ |
| 🩹 **Blessures + H2H affichés** sur la page match (déjà récupérés pour le LLM) | ⭐⭐ | faible | ⬜ |
| 🤖 **IA sur les combinés** — analyse globale d'un ticket entier | ⭐⭐ | moyen | ⬜ |
| 📊 **Page Équipe dédiée** — historique complet + stats d'une équipe | ⭐⭐ | moyen | ⬜ |
| 🎨 **Refonte design** — logo SVG + animations + page d'accueil | ⭐⭐ | moyen | ⬜ |
| 🔬 **Étude avancée** — analyse d'un championnat / équipe / joueur | ⭐⭐⭐ *futur* | élevé | ⬜ |

### 🎯 Backtest ✅
- ✅ Rejouer le modèle sur les saisons passées (matchs terminés)
- ✅ Comparer la prédiction au résultat réel marché par marché (1X2, Over/Under 2.5, Over/Under 1.5, BTTS, double chance)
- ✅ Accuracy **séparée par direction** (quand modèle prédit "Plus" vs "Moins")
- ✅ Page `/backtest` — sélecteur ligue / saison / volume, jauges animées
- ⬜ Mesurer yield si on avait suivi les value bets (nécessite les cotes historiques)

### 🩹 Blessures + H2H sur la page match
- ⬜ Afficher les **blessures/suspensions** des deux équipes (déjà récupérées pour l'IA)
- ⬜ Afficher les **confrontations directes** (H2H) — derniers résultats face-à-face

### 🤖 IA sur les combinés
- ⬜ Depuis la page « Mon ticket », bouton « Analyser avec l'IA »
- ⬜ Le cerveau commente le ticket entier (cohérence, risques, cotes)

### 🎨 Refonte design
- ⬜ **Logo SVG** personnalisé (favicon + thème clair/sombre)
- ⬜ **Animations** : apparition des cartes (stagger), micro-interactions
- ⬜ Page d'accueil plus impactante

### 🔬 Étude avancée (futur)
- ⬜ **Championnat** : tendances saison, Over/Under dominants, value récurrente
- ⬜ **Équipe** : profil détaillé — forme, séries, buts par tranche horaire
- ⬜ **Joueur** : stats, impact absence, lien blessures
- ⬜ **Synthèse IA** : DeepSeek rédige une étude lisible

---

## Phase produit (plus tard)
- ⬜ Comptes utilisateurs + abonnement (freemium / mensuel)
- ⬜ Migration SQLite → PostgreSQL
- ⬜ Historique public vérifiable pour la confiance
- ⬜ Conformité Loto-Québec

## 📱 App mobile Flutter
- ⬜ Application Flutter (iOS + Android)
- ⬜ Mêmes pages : Accueil · Générer · Analyses · Mon ticket · Historique · Performance
- ⬜ Consomme la même API FastAPI (backend partagé)
- ⬜ Notifications push — alertes avant les matchs analysés
- ⬜ Design adapté mobile (bottom nav, cards natives Flutter)

---

## Règle d'or
Un combiné cote 3.00 ≈ 33 % de proba théorique. L'avantage ne vient pas de
« prédire le gagnant » mais de trouver les **erreurs de cote** (value).
**Prouver la précision en backtest avant de vendre quoi que ce soit.**
