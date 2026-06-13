"""Génération de tickets fondés sur la CONFIANCE du consensus.

Nouvelle philosophie d'EDGE : un ticket n'est plus une chasse à la value vers
une cote cible, mais un assemblage des issues les PLUS PROBABLES selon le
consensus multi-modèles. On ne retient un match que si le consensus dégage une
issue à forte confiance (sinon le match est trop incertain → exclu).

Pour chaque match retenu :
  - on prend l'issue simple (1/X/2) si elle dépasse le seuil de confiance ;
  - sinon la meilleure double chance si elle dépasse un seuil (plus haut) ;
  - sinon rien (match écarté).

Les sélections retenues sont triées par probabilité décroissante et regroupées
en tickets : le ticket #1 réunit les paris les plus sûrs.
"""
import logging

from .combines import Combine, Selection

log = logging.getLogger("edge.tickets")

LIBELLES = {
    "1": "Victoire domicile", "X": "Match nul", "2": "Victoire extérieur",
    "1X": "Domicile ou nul (double chance)",
    "12": "Pas de match nul (double chance)",
    "X2": "Extérieur ou nul (double chance)",
}

# Seuils de confiance : une issue simple est retenue à partir de 58 % ; une
# double chance (plus facile) seulement à partir de 72 %.
SEUIL_SIMPLE = 0.58
SEUIL_DOUBLE = 0.72


def selection_confiance(consensus: dict[str, float], cotes: dict[str, float],
                        seuil_simple: float = SEUIL_SIMPLE,
                        seuil_double: float = SEUIL_DOUBLE) -> tuple[str, float] | None:
    """Meilleure issue à forte confiance pour un match, ou None si trop incertain.

    Renvoie (clé_marché, proba_consensus).
    """
    c1 = consensus.get("1", 0.0)
    cX = consensus.get("X", 0.0)
    c2 = consensus.get("2", 0.0)

    cle, p = max((("1", c1), ("X", cX), ("2", c2)), key=lambda kv: kv[1])
    if p >= seuil_simple:
        return cle, p

    dc = {"1X": c1 + cX, "12": c1 + c2, "X2": cX + c2}
    cle_dc, p_dc = max(dc.items(), key=lambda kv: kv[1])
    if p_dc >= seuil_double:
        return cle_dc, p_dc

    return None


def construire_selection(match: str, ligue: str, fixture_id: int, date: str,
                         cle: str, proba: float, cotes: dict[str, float]) -> Selection:
    """Construit un objet Selection pour une issue retenue du consensus."""
    cote = cotes.get(cle, 0.0) or 0.0
    return Selection(
        match=match, marche=LIBELLES.get(cle, cle), proba=proba, cote=cote,
        ligue=ligue, fixture_id=fixture_id, cle=cle, match_date=date,
    )


def generer_tickets_confiance(selections: list[Selection], nb_tickets: int = 5,
                              taille: int = 3, taille_min: int = 2) -> list[Combine]:
    """Regroupe les sélections à forte confiance en tickets.

    Les sélections sont triées par probabilité décroissante puis découpées en
    paquets de `taille` (chaque match utilisé une seule fois). Le ticket #1
    contient donc les paris les plus sûrs. Un dernier paquet incomplet devient
    un ticket s'il atteint `taille_min`.
    """
    pool = sorted(selections, key=lambda s: s.proba, reverse=True)

    tickets: list[Combine] = []
    paquet: list[Selection] = []
    vus_dans_paquet: set[str] = set()

    for s in pool:
        if s.match in vus_dans_paquet:
            continue
        paquet.append(s)
        vus_dans_paquet.add(s.match)
        if len(paquet) == taille:
            tickets.append(Combine(list(paquet)))
            paquet, vus_dans_paquet = [], set()
            if len(tickets) >= nb_tickets:
                return tickets

    if len(paquet) >= taille_min and len(tickets) < nb_tickets:
        tickets.append(Combine(list(paquet)))

    return tickets
