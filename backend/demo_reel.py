"""Démo RÉELLE de bout en bout (contourne le piège du plan gratuit).

Stats d'équipe : saison 2024 (accessible sur le plan gratuit)
Cotes          : matchs RÉELS d'aujourd'hui (saison courante)

=> prouve que toute la chaîne fonctionne sur de vraies données.
Avec une clé donnant les deux sur la même saison, on remplace juste STATS_SEASON.
"""
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

from src.api_client import ApiFootball
from src.combines import Selection, generer_combines
from src.odds_parser import recuperer_cotes
from src.pipeline import LIBELLES, fixtures_depuis_reponse
from src.poisson import compute_probabilities
from src.team_stats import buts_attendus, recuperer_stats

STATS_SEASON = 2024          # saison des stats (accessible plan gratuit)
LIGUE = 200                  # Botola Pro (Maroc)
DATE = "2026-06-03"

api = ApiFootball()

# Matchs réels d'aujourd'hui dans la Botola
data = api.get("fixtures", {"date": DATE})
fixtures = fixtures_depuis_reponse(data["response"], league_id=LIGUE)
print(f"{len(fixtures)} matchs Botola aujourd'hui.\n")

pool: list[Selection] = []
for fx in fixtures:
    # stats 2024 (on force la saison accessible)
    dom = recuperer_stats(api, LIGUE, STATS_SEASON, fx.home_id)
    ext = recuperer_stats(api, LIGUE, STATS_SEASON, fx.away_id)
    if not dom or not ext or not dom.fiable or not ext.fiable:
        print(f"⚠ {fx.home_name} - {fx.away_name} : stats 2024 indisponibles, ignoré.")
        continue

    lam_dom, lam_ext = buts_attendus(dom, ext)
    probas = compute_probabilities(lam_dom, lam_ext).as_market_dict()
    cotes = recuperer_cotes(api, fx.fixture_id)
    if not cotes:
        print(f"⚠ {fx.home_name} - {fx.away_name} : cotes indisponibles, ignoré.")
        continue

    label = f"{fx.home_name} - {fx.away_name}"
    print(f"✔ {label}  (λ {lam_dom:.2f}-{lam_ext:.2f})")
    for cle, cote in cotes.items():
        p = probas.get(cle)
        if p is None:
            continue
        s = Selection(label, LIBELLES.get(cle, cle), proba=p, cote=cote)
        if s.est_value_bet:
            print(f"     VALUE: {s.marche:34} proba {p:.0%} @ {cote:.2f} (value {s.value:+.0%})")
        pool.append(s)

combines = generer_combines(pool, nb_combines=5, cote_cible=3.0, tolerance=0.6)

print("\n" + "=" * 62)
print(f"COMBINÉS GÉNÉRÉS : {len(combines)}")
print("=" * 62)
for i, c in enumerate(combines, 1):
    print(f"\n#{i}  Cote {c.cote_totale:.2f} | Proba {c.proba_combinee:.1%} "
          f"| Value {c.value_combinee:+.1%}")
    for s in c.selections:
        print(f"     • {s.match:34} {s.marche:32} @ {s.cote:.2f} (proba {s.proba:.0%})")
