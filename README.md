# BET — Générateur de tickets (Mise-o-jeu)

Outil d'analyse statistique de paris sportifs (football). Il scanne
automatiquement les matchs des championnats offerts par Mise-o-jeu,
calcule des probabilités par **loi de Poisson** (100 % statistique, sans
machine learning), détecte les *value bets* et génère des **combinés**
à cote cible (~3.00).

## Principe

```
API-Football (matchs + stats + cotes consensus)
   → filtre liste blanche Mise-o-jeu (matchs jouables uniquement)
   → moteur Poisson (proba 1X2 / Over-Under / BTTS / double chance)
   → détection value bets
   → génération automatique des tickets
```

La cote affichée est le **consensus** de ~13 bookmakers (Bet365, Pinnacle,
1xBet…). Mise-o-jeu n'expose pas d'API publique ; ses cotes sont proches
du consensus (en un peu moins généreuses, marge ~4 %).

## Installation

```bash
pip install -r requirements.txt
cp .env.example .env      # puis mettre ta clé API-Football dans .env
```

## Utilisation

```bash
python app.py             # serveur web -> http://127.0.0.1:8000
```

Un seul bouton : **« Générer les tickets »** lance le scan automatique.

Scripts utiles :
- `python test_cle.py` — vérifie la clé API et le quota
- `python matchs_du_jour.py` — liste les matchs du jour
- `python demo_poisson.py` / `demo_combines.py` — démos hors-ligne

## Structure

| Fichier | Rôle |
|---|---|
| `src/api_client.py` | Client API-Football + cache disque + anti rate-limit |
| `src/poisson.py` | Moteur de probabilité (loi de Poisson) |
| `src/team_stats.py` | Stats équipes (clubs et sélections nationales) → buts attendus |
| `src/odds_parser.py` | Extraction des cotes (consensus bookmakers) |
| `src/combines.py` | Value bets + génération des combinés |
| `src/ligues_mise_o_jeu.py` | Liste blanche des championnats Mise-o-jeu (validateur) |
| `src/pipeline.py` | Orchestrateur → JSON |
| `app.py` | Serveur web (FastAPI) |

## Avertissement

Les paris sportifs comportent des risques. Cet outil fournit des
probabilités statistiques, pas des certitudes. À backtester avant tout
usage réel. Jouez de manière responsable.
