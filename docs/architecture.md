# Architecture

## Vue d'ensemble

```
                ┌─────────────── backend/ ───────────────┐
API-Football →  │ api_client → team_stats → poisson       │
(stats, cotes)  │                              ↓          │
                │ odds_parser → pipeline → combines       │
                │      ↑            ↓                      │
                │ ligues_mise_o_jeu (validateur)          │
                │                   ↓                      │
                │              app.py (FastAPI)            │
                └───────────────────┬─────────────────────┘
                                    │  JSON
                            frontend/index.html
```

## Flux complet (scan automatique)

1. **app.py** reçoit `/api/generer` (un seul bouton côté frontend).
2. Il scanne les **dates accessibles** (aujourd'hui ± 1 sur le plan gratuit).
3. **ligues_mise_o_jeu** filtre : on ne garde que les championnats offerts
   par Mise-o-jeu (validateur → aucun match injouable).
4. Pour chaque match :
   - **team_stats** calcule la force des équipes (buts marqués/encaissés).
     - mode *club* : stats de la saison de ligue.
     - mode *national* : derniers matchs internationaux (Coupe du Monde…).
   - **poisson** transforme ça en probabilités de tous les marchés
     (1X2, Over/Under 2.5, BTTS, double chance).
   - **odds_parser** récupère les cotes (consensus + Pinnacle → estimation Mise-o-jeu).
5. **combines** détecte les *value bets* et assemble les combinés
   (cote cible ~3.00, sélections diversifiées).
6. Résultat renvoyé en **JSON structuré** (pensé pour être lu aussi par un LLM).

## Modules

| Module | Rôle |
|---|---|
| `api_client.py` | Appels API-Football + cache disque + anti rate-limit (429) |
| `team_stats.py` | Stats équipes → buts attendus (λ). Modes club et national |
| `poisson.py` | Loi de Poisson → probabilités de chaque marché |
| `odds_parser.py` | Cotes : consensus, Pinnacle, estimation Mise-o-jeu |
| `combines.py` | Value bets + génération des combinés |
| `ligues_mise_o_jeu.py` | Liste blanche des championnats Mise-o-jeu (validateur) |
| `pipeline.py` | Orchestrateur de bout en bout → JSON |
| `app.py` | Serveur web FastAPI |

## Le moteur Poisson (cœur)

On estime les buts attendus de chaque équipe (λ), puis on calcule la
probabilité de **chaque score exact** via la loi de Poisson, et on agrège :

- λ_domicile = (attaque domicile + faiblesse défensive adverse) / 2
- λ_extérieur = (attaque extérieur + faiblesse défensive adverse) / 2
- P(score h-a) = Poisson(h, λ_dom) × Poisson(a, λ_ext)
- 1X2, Over/Under, BTTS, double chance = sommes sur la grille des scores.

100 % statistique, auditable, sans machine learning.
