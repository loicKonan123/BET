"""Générateur de combinés à cote cible (~3.00) à partir de value bets.

Principe :
1. Une "sélection" = un pari simple (ex: "PSG vainqueur") avec :
   - notre probabilité calculée (Poisson)
   - la cote du bookmaker
2. On ne garde que les VALUE BETS : paris où notre proba > proba implicite
   de la cote. C'est mathématiquement la SEULE façon d'être rentable à long terme.
3. On assemble des combinés dont la cote totale vise ~3.00, en maximisant
   la probabilité combinée (donc le taux de réussite attendu).
"""
from dataclasses import dataclass
from itertools import combinations


@dataclass
class Selection:
    match: str          # "PSG - Lyon"
    marche: str         # "1 (domicile)", "Over 2.5", "BTTS oui"...
    proba: float        # notre probabilité calculée (0..1)
    cote: float         # cote du bookmaker
    ligue: str = ""       # nom du championnat (pour retrouver le match sur Mise-o-jeu)
    fixture_id: int = 0   # ID API-Football (pour grader le résultat)
    cle: str = ""         # clé marché brute ("1", "X", "over_2.5", …)
    match_date: str = ""  # datetime ISO du match (pour ne checker qu'après coup)

    @property
    def proba_implicite(self) -> float:
        """Probabilité que le bookmaker "facture" via la cote."""
        return 1 / self.cote

    @property
    def value(self) -> float:
        """Espérance de gain (EV). > 0 => pari rentable à long terme."""
        return self.proba * self.cote - 1

    @property
    def est_value_bet(self) -> bool:
        return self.value > 0


@dataclass
class Combine:
    selections: list[Selection]

    @property
    def cote_totale(self) -> float:
        c = 1.0
        for s in self.selections:
            c *= s.cote
        return c

    @property
    def proba_combinee(self) -> float:
        """Proba que TOUTES les sélections passent (on les suppose indépendantes)."""
        p = 1.0
        for s in self.selections:
            p *= s.proba
        return p

    @property
    def value_combinee(self) -> float:
        return self.proba_combinee * self.cote_totale - 1

    def resume(self) -> str:
        lignes = [
            f"  • {s.match} | {s.marche} @ {s.cote:.2f} "
            f"(proba {s.proba:.0%}, value {s.value:+.0%})"
            for s in self.selections
        ]
        return (
            f"Cote totale : {self.cote_totale:.2f} | "
            f"Proba réussite : {self.proba_combinee:.1%} | "
            f"Value : {self.value_combinee:+.1%}\n" + "\n".join(lignes)
        )


def generer_combines(
    selections: list[Selection],
    nb_combines: int = 5,
    cote_cible: float = 3.0,
    tolerance: float = 0.5,
    taille_min: int = 2,
    taille_max: int = 4,
    value_min: float = 0.0,
) -> list[Combine]:
    """Génère les meilleurs combinés visant `cote_cible`.

    - On part uniquement des value bets (value > value_min).
    - On teste toutes les combinaisons de taille [taille_min, taille_max].
    - On garde celles dont la cote tombe dans [cote_cible±tolerance].
    - On les classe par probabilité de réussite décroissante.
    - On évite de réutiliser deux fois le même match dans des combinés différents
      (diversification) tant que possible.
    """
    pool = [s for s in selections if s.value > value_min]

    candidats: list[Combine] = []
    for taille in range(taille_min, taille_max + 1):
        for combo in combinations(pool, taille):
            # un même match ne doit pas apparaître 2x dans le même combiné
            matchs = [s.match for s in combo]
            if len(set(matchs)) != len(matchs):
                continue
            c = Combine(list(combo))
            if abs(c.cote_totale - cote_cible) <= tolerance:
                candidats.append(c)

    # tri : meilleure proba de réussite d'abord, puis meilleure value
    candidats.sort(key=lambda c: (c.proba_combinee, c.value_combinee), reverse=True)

    def identites(c: Combine) -> set[tuple[str, str]]:
        return {(s.match, s.marche) for s in c.selections}

    # Tier 1 : tickets totalement distincts (aucune sélection réutilisée)
    retenus: list[Combine] = []
    sel_utilisees: set[tuple[str, str]] = set()
    for c in candidats:
        ids = identites(c)
        if ids & sel_utilisees:
            continue
        retenus.append(c)
        sel_utilisees |= ids
        if len(retenus) >= nb_combines:
            return retenus

    # Tier 2 : compléter en autorisant des sélections partagées, mais jamais
    # deux fois exactement le même combiné.
    for c in candidats:
        if c in retenus:
            continue
        retenus.append(c)
        if len(retenus) >= nb_combines:
            break

    return retenus[:nb_combines]
