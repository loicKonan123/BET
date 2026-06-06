"""Démo du moteur Poisson sur un match fictif — ne consomme AUCUNE requête API."""
import sys

sys.stdout.reconfigure(encoding="utf-8")

from src.poisson import TeamStrength, analyser_match

# Exemple : une grosse équipe à domicile contre une équipe moyenne
# attack=1.4 => marque 40% de plus que la moyenne du championnat
# defense=0.7 => encaisse 30% de moins que la moyenne (bonne défense)
domicile = TeamStrength(attack=1.4, defense=0.7)
exterieur = TeamStrength(attack=0.9, defense=1.2)

proba = analyser_match(domicile, exterieur)

print("=" * 55)
print("ANALYSE DU MATCH (modèle Poisson)")
print("=" * 55)
print(f"Buts attendus domicile  : {proba.expected_home_goals:.2f}")
print(f"Buts attendus extérieur : {proba.expected_away_goals:.2f}")
print("-" * 55)
print(f"Victoire domicile (1) : {proba.home_win:6.1%}")
print(f"Match nul (X)         : {proba.draw:6.1%}")
print(f"Victoire extérieur(2) : {proba.away_win:6.1%}")
print("-" * 55)
print(f"Plus de 2.5 buts      : {proba.over_25:6.1%}")
print(f"Moins de 2.5 buts     : {proba.under_25:6.1%}")
print(f"Les 2 marquent (oui)  : {proba.btts_yes:6.1%}")
print(f"Les 2 marquent (non)  : {proba.btts_no:6.1%}")
print("=" * 55)

# Vérification : les probas 1X2 doivent sommer à 100%
total = proba.home_win + proba.draw + proba.away_win
print(f"\nVérif (1+X+2 doit faire 100%) : {total:.1%}")
