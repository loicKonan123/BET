# Plan / Feuille de route — EDGE

Légende : ✅ fait · 🔄 en cours · ⬜ à faire

EDGE = plateforme de **conseil/analyse** pour Mise-o-jeu (Loto-Québec).
On ne mise pas dans l'app : on analyse, on conseille, on suit la précision des pronostics.

---

## ✅ Déjà fait

### Moteur statistique
- ✅ Client API-Football (**PRO**) + cache disque + anti rate-limit
- ✅ Moteur **Poisson** (1X2, Over/Under 2.5, Over/Under 1.5, BTTS, double chance)
- ✅ Stats équipes → buts attendus — mode **club** ET mode **équipes nationales** (CDM)
- ✅ Détection des **value bets** + génération de **combinés** (cote ~3.00)
- ✅ Validateur **Mise-o-jeu** (liste blanche) → jamais de match injouable
- ✅ Scan automatique multi-dates
- ✅ Cotes consensus (~13 bookmakers, dont Pinnacle)

### Application web (Next.js + FastAPI)
- ✅ Design **Apex Velocity** — glassmorphism, thème clair/sombre
- ✅ Layout responsive — max-width grand écran (32 pouces), centré
- ✅ Pages : Accueil · Générer · Analyses · Performance · Historique · Mon ticket
- ✅ Page match détaillée : conseil, barre 1X2, forme, tous les marchés, classement, compos
- ✅ **Compositions sur terrain horizontal** — SVG avec joueurs positionnés via `grid`, photos joueurs circulaires (API-Football), remplaçants avec photo
- ✅ **Classement par groupe** en tabs (Coupe du Monde compatible)
- ✅ Derniers matchs avec scores réels (5 par équipe)
- ✅ Heures Montréal (AM/PM)

### Tickets & suivi
- ✅ Tickets auto-générés + sauvegarde + historique
- ✅ Ticket builder manuel (panier persistant localStorage)
- ✅ Auto-settlement (grading automatique via score API-Football)
- ✅ Analytics : taux de réussite, tickets gagnés/perdus/en attente

### Cerveau IA (DeepSeek)
- ✅ Analyste DeepSeek (reasoner) : raisonne sur un dossier complet → analyse + conseil nuancé
- ✅ Cache permanent des analyses IA
- ✅ Règle absolue : le LLM ne calcule jamais les probas (Poisson = vérité)

### Backtest
- ✅ Rejouer le modèle sur les saisons passées (matchs terminés)
- ✅ Accuracy séparée par direction (Over vs Under, BTTS Oui vs Non, etc.)
- ✅ Page `/backtest` — sélecteur ligue / saison / volume, jauges animées SVG
- ✅ Tableau détaillé match par match avec ✓/✗ par marché

### Live & Scores
- ✅ Endpoint `/api/live` — matchs en cours dans nos ligues (sans cache)
- ✅ Endpoint `/api/score/{id}` — score + événements temps réel (sans cache)
- ✅ **LiveWidget dans la sidebar** — matchs en direct avec score + minute, pulsant en rouge, clicable
- ✅ **Score live sur la page match** — badge LIVE pulsant, score en grand, événements (⚽ buts, 🟨🟥 cartons), polling toutes les 60s, auto-stop à FT
- ✅ **Page Scores `/scores`** — navigation par date (← →), tous les matchs de nos ligues (passés · live · à venir), groupés par compétition, rien ne disparaît jamais

### Équipes & Joueurs
- ✅ Endpoint `/api/team/{id}` — profil + 15 derniers matchs + stats calculées
- ✅ Endpoint `/api/player/{id}` — infos + stats saison en cours
- ✅ **Page Équipe** `/team/[id]` — logo, stade, bilan W/D/L, moyennes buts, historique clicable
- ✅ **Page Joueur** `/player/[id]` — photo, poste, âge, stats saison (buts, assists, minutes, note)
- ✅ **Équipes clicables** sur la page match (logos → `/team/[id]`)
- ✅ **Joueurs clicables** sur le terrain SVG (token → `/player/[id]`)
- ✅ **Lien équipe** depuis la page joueur (→ `/team/[id]`)

### Navigation & UX
- ✅ **Onglets sur la page match** — 4 tabs : Analyse · Compos · Classement · Forme & H2H
- ✅ **H2H (confrontations directes)** — endpoint `/api` + affichage dans l'onglet Forme
- ✅ **Bouton Retour contextuel** — `router.back()` fonctionne depuis `/scores` ou `/analyses`
- ✅ **Auto-switch onglet Compos** — si les compositions sont disponibles, l'onglet Compos est sélectionné automatiquement

---

## 🔄 Prioritaires

| # | Piste | Valeur | Effort |
|---|-------|--------|--------|
| 1 | 🤖 **IA sur les combinés** — analyser un ticket entier avec DeepSeek | ⭐⭐ | moyen |
| 2 | 🎨 **Refonte design** — logo SVG, animations stagger, page accueil | ⭐⭐ | moyen |
| 3 | 🔬 **Étude avancée** — analyse d'un championnat / équipe | ⭐⭐⭐ | élevé |

---

## ⬜ Détail des prochaines features

### 🤖 IA sur les combinés
- Depuis "Mon ticket" → bouton "Analyser avec l'IA"
- DeepSeek commente la cohérence du ticket, les risques, les cotes
- Utilise les analyses individuelles déjà en cache

### 🎨 Refonte design
- Logo SVG personnalisé (favicon + nav)
- Animations : apparition des cartes en stagger
- Page d'accueil plus impactante (stats live, dernier backtest, score live)

### 🔬 Étude avancée (futur)
- Championnat : tendances saison, Over/Under dominants, value récurrente
- Équipe : profil détaillé — forme, séries, buts par tranche horaire
- Synthèse IA : DeepSeek rédige une étude lisible

---

## 📱 App mobile Flutter (futur)
- Application Flutter (iOS + Android)
- Mêmes pages : Accueil · Scores · Analyses · Mon ticket · Historique · Performance
- Consomme la même API FastAPI (backend partagé)
- Notifications push — alertes avant les matchs analysés
- Design adapté mobile (bottom nav, cards natives Flutter)

---

## 🏗️ Architecture actuelle

```
frontend/              ← Next.js 14, TypeScript, Tailwind v4
  app/
    scores/            ← navigation par date, tous les matchs
    analyses/          ← matchs à venir analysés
    match/[id]/        ← détail match : analyse + live + compos terrain
    backtest/          ← rejouer le modèle sur saisons passées
    ticket-builder/    ← panier manuel
    history/           ← tickets sauvegardés
    analytics/         ← performance
    components/
      PitchView.tsx    ← terrain SVG horizontal, photos joueurs
      LiveWidget.tsx   ← widget live dans sidebar
      Shell.tsx        ← nav + sidebar + layout
    hooks/
      useLiveScore.ts  ← polling score/min/events toutes les 60s
      useLiveMatches.ts← polling matchs en cours toutes les 60s
    lib/
      api.ts           ← tous les types + fonctions fetch
      ligues.ts        ← liste des ligues

backend/               ← FastAPI, Python
  app.py               ← tous les endpoints
  src/
    api_client.py      ← client API-Football + cache disque
    poisson.py         ← modèle Poisson + marchés
    pipeline.py        ← scan fixtures + analyse
    backtest.py        ← replay modèle sur historique
    analyste.py        ← cerveau DeepSeek
    store.py           ← SQLite (tickets, analyses IA)
    ligues_mise_o_jeu.py ← liste blanche Mise-o-jeu

docs/
  plan.md              ← ce fichier
```

---

## Quota API-Football (7 500 req/jour)
| Usage | Req/jour |
|---|---|
| Scan analyses (daily) | ~150 |
| Page Scores (par date visitée, cache) | ~30 |
| Live polling sidebar (60s, matchs actifs) | ~100-300 |
| Live score page match (60s) | ~90 par match ouvert |
| Pages équipes/joueurs (cache, 1 seule fois) | ~200 premier jour |
| **Total réaliste** | **~500-800 req/jour** |
| **Marge** | **~6700 req/jour disponibles** |

---

## Règle d'or
Un combiné cote 3.00 ≈ 33 % de proba théorique. L'avantage ne vient pas de
« prédire le gagnant » mais de trouver les **erreurs de cote** (value).
**Prouver la précision en backtest avant de vendre quoi que ce soit.**
