"""Inspecte la structure JSON des stats d'équipe et des cotes (2 requêtes)."""
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

from src.api_client import ApiFootball

api = ApiFootball()

# 1) Stats de Raja Casablanca
stats = api.get("teams/statistics", {"league": 200, "season": 2025, "team": 976})
resp = stats["response"]
print("=" * 60)
print("STRUCTURE teams/statistics — clés de premier niveau :")
print(list(resp.keys()))
print("\n--- goals.for ---")
print(json.dumps(resp.get("goals", {}).get("for", {}), ensure_ascii=False, indent=2))
print("\n--- goals.against ---")
print(json.dumps(resp.get("goals", {}).get("against", {}), ensure_ascii=False, indent=2))
print("\n--- fixtures (matchs joués) ---")
print(json.dumps(resp.get("fixtures", {}), ensure_ascii=False, indent=2))

# 2) Cotes pour le match Raja - Berkane
odds = api.get("odds", {"fixture": 1545541})
print("\n" + "=" * 60)
print(f"STRUCTURE odds — {odds.get('results', 0)} résultat(s)")
oresp = odds.get("response", [])
if oresp:
    bm = oresp[0].get("bookmakers", [])
    print(f"Bookmakers disponibles : {len(bm)}")
    if bm:
        print(f"1er bookmaker : {bm[0]['name']}")
        print("Marchés (bets) proposés :")
        for bet in bm[0].get("bets", []):
            print(f"  id={bet['id']:>3}  {bet['name']}  -> {[v['value'] for v in bet['values'][:6]]}")
else:
    print("Aucune cote disponible pour ce match.")
