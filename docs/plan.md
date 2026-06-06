# Plan / Feuille de route — BET

Légende : ✅ fait · 🔄 en cours · ⬜ à faire

## Phase 1 — Moteur (MVP) ✅

- ✅ Client API-Football + cache disque + anti rate-limit (429)
- ✅ Moteur Poisson (1X2, Over/Under 2.5, BTTS, double chance)
- ✅ Stats équipes → buts attendus (mode club)
- ✅ Détection des value bets + génération des combinés (cote ~3.00)
- ✅ Liste blanche Mise-o-jeu comme **validateur** (matchs jouables uniquement)
- ✅ Scan **automatique** multi-dates (un seul bouton, zéro choix manuel)
- ✅ Mode **équipes nationales** (Coupe du Monde, Euro… via matchs internationaux)
- ✅ Interface web (FastAPI + HTML)
- ✅ Réorganisation `backend/` + `frontend/` + `docs/`
- ✅ Projet sur GitHub (clé `.env` protégée)

## Phase 2 — Cotes réalistes 🔄

- 🔄 Cotes : consensus + **Pinnacle** (le plus précis) → **estimation Mise-o-jeu**
  (base Pinnacle/consensus rabaissée de la marge ~4,5 %)
- ⬜ Afficher dans l'interface : cote estimée Mise-o-jeu + cote consensus (référence)
- ⬜ Seuil de value ajusté à la marge Mise-o-jeu

## Phase 3 — Passage en prod (clé PRO 19 $) ⬜

- ⬜ Nouvelle clé dans `.env`
- ⬜ `stats_season` = saison courante
- ⬜ Élargir la fenêtre de dates (semaine entière)
- ⬜ Cotes en direct + forme à jour
- ⬜ Coupe du Monde 2026 (à partir du 11 juin)

## Phase 4 — Backtest (CRUCIAL avant de vendre) ⬜

- ⬜ Rejouer le modèle sur 2022-2024 (stats accessibles)
- ⬜ Mesurer ROI / yield / taux de réussite des combinés
- ⬜ Valider que le modèle bat la clôture du marché
- ⬜ Ne vendre aux clients que si rentable sur 1000+ matchs

## Phase 5 — Application produit ⬜

- ⬜ Backend FastAPI complet (endpoints, comptes, historique)
- ⬜ Base PostgreSQL (matchs, cotes, tickets, résultats, bankroll)
- ⬜ Frontend Next.js (dashboard, suivi ROI, historique vérifiable)
- ⬜ Modèle d'abonnement (freemium / mensuel)
- ⬜ Gestion de bankroll (critère de Kelly fractionnel)

## Phase 6 — Couche IA (LLM) ⬜

- ⬜ Le LLM lit la sortie JSON du moteur et **explique** chaque pari
  en langage naturel (le calcul reste statistique, l'IA habille)
- ⬜ Génération de résumés / justifications pour les clients

## Phase 7 — Lancement ⬜

- ⬜ Jeu responsable (avertissements, limites)
- ⬜ Conformité légale (Québec / Loto-Québec)
- ⬜ Transparence : historique public des paris (gagnés ET perdus)
- ⬜ Acquisition des premiers clients

---

## Règle d'or

Un combiné cote 3.00 ≈ 33 % de proba théorique. L'avantage ne vient pas
de « prédire le gagnant » mais de trouver les **erreurs de cote** (value).
**Prouver la rentabilité en backtest avant de vendre quoi que ce soit.**
