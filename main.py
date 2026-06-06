"""Lance le pipeline complet et génère les 5 combinés.

Usage :
    python main.py                       # défaut : Premier League, saison 2023, 5 matchs
    python main.py 39 2023 8             # ligue 39, saison 2023, 8 matchs max
    python main.py 200 2023 6            # Botola Pro (Maroc)

Économie de quota : chaque match coûte 3 requêtes. La 1re exécution remplit
le cache ; les suivantes sont gratuites.
"""
import sys

sys.stdout.reconfigure(encoding="utf-8")

from src.api_client import ApiFootball
from src.pipeline import fixtures_depuis_reponse, generer_pronostics, sauver_json


def main():
    league = int(sys.argv[1]) if len(sys.argv) > 1 else 39
    season = int(sys.argv[2]) if len(sys.argv) > 2 else 2023
    nb_max = int(sys.argv[3]) if len(sys.argv) > 3 else 5

    api = ApiFootball()

    print(f"Récupération des matchs : ligue={league} saison={season} ...")
    data = api.get("fixtures", {"league": league, "season": season})
    fixtures = fixtures_depuis_reponse(data.get("response", []))
    print(f"  {len(fixtures)} matchs trouvés. Analyse des {nb_max} premiers "
          f"(coût ~{nb_max * 3} requêtes API).")

    fixtures = fixtures[:nb_max]
    resultat = generer_pronostics(api, fixtures, nb_combines=5, cote_cible=3.0)

    sauver_json(resultat, "resultats.json")

    print("\n" + "=" * 62)
    print(f"ANALYSE TERMINÉE — {resultat['nb_matchs_analyses']} matchs exploitables")
    print(f"({len(fixtures)} demandés ; les autres n'avaient pas stats+cotes)")
    print("=" * 62)

    if not resultat["combines"]:
        print("\n⚠ Aucun combiné généré (pas assez de value bets ou de cotes).")
        print("  -> Souvent normal sur le plan gratuit : cotes historiques limitées.")
        print("  -> Le pipeline fonctionne ; il suffira d'une clé avec accès aux cotes.")
        return

    for i, c in enumerate(resultat["combines"], 1):
        print(f"\n#{i}  Cote {c['cote_totale']:.2f} | "
              f"Proba réussite {c['proba_reussite']:.1%} | "
              f"Value {c['value']:+.1%}")
        for s in c["selections"]:
            print(f"     • {s['match']:32} {s['marche']:34} @ {s['cote']:.2f} "
                  f"(proba {s['proba']:.0%})")

    print(f"\n✔ Détails complets enregistrés dans resultats.json")


if __name__ == "__main__":
    main()
