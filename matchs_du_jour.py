"""Reconnaissance : quels matchs se jouent aujourd'hui (ou une date donnée).

Coûte 1 requête API (mise en cache ensuite). Sert à voir quels championnats
sont actifs — utile en juin où l'Europe est en pause.

Usage :
    python matchs_du_jour.py            # aujourd'hui
    python matchs_du_jour.py 2026-06-14 # une date précise
"""
import sys
from collections import defaultdict
from datetime import date

sys.stdout.reconfigure(encoding="utf-8")

from src.api_client import ApiFootball


def main():
    jour = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()

    api = ApiFootball()
    data = api.get("fixtures", {"date": jour})

    fixtures = data.get("response", [])
    print("=" * 60)
    print(f"MATCHS DU {jour} — {len(fixtures)} matchs trouvés")
    print(f"(requêtes API utilisées aujourd'hui : {data.get('results', '?')} résultats)")
    print("=" * 60)

    if not fixtures:
        print("Aucun match ce jour-là.")
        return

    # Regroupe par championnat
    par_ligue = defaultdict(list)
    for f in fixtures:
        ligue = f["league"]
        cle = f"{ligue['country']} — {ligue['name']} (id={ligue['id']})"
        par_ligue[cle].append(f)

    # Affiche les ligues triées par nombre de matchs
    for ligue, matchs in sorted(par_ligue.items(), key=lambda x: -len(x[1])):
        print(f"\n▶ {ligue}  [{len(matchs)} matchs]")
        for f in matchs[:8]:  # max 8 par ligue pour rester lisible
            dom = f["teams"]["home"]["name"]
            ext = f["teams"]["away"]["name"]
            heure = f["fixture"]["date"][11:16]
            statut = f["fixture"]["status"]["short"]
            print(f"    {heure}  {dom} - {ext}  [{statut}]")
        if len(matchs) > 8:
            print(f"    ... et {len(matchs) - 8} autres")


if __name__ == "__main__":
    main()
