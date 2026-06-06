"""Démo : génère 5 combinés à cote ~3.00 — ne consomme AUCUNE requête API.

Les sélections ci-dessous sont fictives, juste pour montrer la mécanique.
En vrai, `proba` viendra du moteur Poisson et `cote` de l'API.
"""
import sys

sys.stdout.reconfigure(encoding="utf-8")

from src.combines import Selection, generer_combines

# Pool de paris candidats (proba = notre calcul Poisson, cote = bookmaker)
selections = [
    Selection("PSG - Lyon",          "1 (domicile)", proba=0.72, cote=1.55),
    Selection("Man City - Burnley",  "1 (domicile)", proba=0.78, cote=1.45),
    Selection("Bayern - Augsburg",   "Over 2.5",     proba=0.70, cote=1.50),
    Selection("Real - Getafe",       "1 (domicile)", proba=0.68, cote=1.50),
    Selection("Inter - Empoli",      "BTTS non",     proba=0.60, cote=1.60),
    Selection("Liverpool - Brighton","Over 2.5",     proba=0.65, cote=1.55),
    Selection("Arsenal - Luton",     "1 (domicile)", proba=0.75, cote=1.40),
    Selection("Juventus - Salernit.","1 (domicile)", proba=0.66, cote=1.50),
]

# On affiche d'abord lesquels sont des value bets
print("=" * 60)
print("ANALYSE DES VALUE BETS")
print("=" * 60)
for s in selections:
    tag = "✔ VALUE" if s.est_value_bet else "✗ skip  "
    print(f"{tag} | {s.match:24} {s.marche:14} "
          f"proba {s.proba:.0%} vs cote-impl {s.proba_implicite:.0%} "
          f"=> value {s.value:+.0%}")

combines = generer_combines(selections, nb_combines=5, cote_cible=3.0, tolerance=0.5)

print("\n" + "=" * 60)
print(f"LES {len(combines)} COMBINÉS PROPOSÉS (cote ~3.00)")
print("=" * 60)
for i, c in enumerate(combines, 1):
    print(f"\n#{i}  {c.resume()}")
