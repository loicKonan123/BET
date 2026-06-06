# Mise-o-jeu & API — décisions et contraintes

## Mise-o-jeu+ (Loto-Québec)

Bookmaker légal monopole du Québec. Règles utiles :

- **Combo = 2 à 12 prédictions.** C'est notre produit (combinés).
- **Aucune corrélation** autorisée entre les prédictions d'un combo.
  → Notre moteur respecte déjà ça : 1 seule sélection par match, jamais
  deux marchés du même match dans un combo.
- Mises **2 $ à 100 $**, cotes décimales.
- **Marges élevées** : ~1.85/1.85 au lieu de 1.91 ailleurs (≈ 4 % de plus).

## Les cotes : aucune API abordable pour Mise-o-jeu

- The Odds API ne couvre pas le Canada.
- OpticOdds (~5 000 $/mois) et Betstamp PRO : hors budget.
- Scraping de espacejeux.com : **bloqué** (handshake TLS refusé, anti-bot).

### Solution retenue

On part des **cotes consensus** d'API-Football (~13 bookmakers dont
**Pinnacle**, le plus précis), puis :

1. base = Pinnacle si disponible, sinon moyenne consensus ;
2. cote estimée Mise-o-jeu = base / (1 + marge), marge ≈ 4,5 %.

→ La cote affichée approche ce que Mise-o-jeu donnera réellement.
→ Les matchs sont garantis jouables grâce au **validateur** (liste blanche).

## API-Football

- Endpoint direct : `https://v3.football.api-sports.io`, header `x-apisports-key`.
- Clé dans `backend/.env` (jamais versionnée).

### Plan gratuit — limites rencontrées

| Limite | Détail |
|---|---|
| Saisons stats | 2022-2024 uniquement (saison courante bloquée) |
| Paramètre `last` | interdit |
| Fixtures par date | aujourd'hui ± 1 jour seulement |
| Quota | 100 req/jour, 10 req/min |

### Plan PRO (19 $/mois) — recommandé

Débloque **tout** : saison courante, `last`, n'importe quelle date,
7 500 req/jour (~300/min). Largement suffisant (usage réel ≈ 500-900/jour).

Pour basculer en prod : nouvelle clé dans `.env`, `stats_season` =
saison courante dans `app.py`, et élargir la fenêtre de dates.

## Liste blanche des championnats

`backend/src/ligues_mise_o_jeu.py` mappe les compétitions offertes par
Mise-o-jeu vers leurs IDs API-Football. En été (Europe en pause), ce sont
surtout les championnats **sud-américains** et la **Coupe du Monde** qui
alimentent le scan. À ajuster selon l'offre réelle de Mise-o-jeu.
