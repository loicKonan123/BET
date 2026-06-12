"""Système de notation Elo pour le football (style World Football Elo / 538).

L'Elo résout le problème que le Poisson par moyennes ne voit pas : la FORCE DE
CALENDRIER. Marquer 1.5 but/match contre des adversaires faibles ne vaut pas
1.5 but/match contre des cadors. En Elo, battre un fort rapporte beaucoup de
points, écraser un faible en rapporte peu — la note reflète la vraie force.

Principes (issus de la recherche) :
  - 400 points d'écart Elo ≈ 1 but de supériorité attendue.
  - 100 points d'écart ≈ 64% de victoire sur terrain neutre.
  - Le K-facteur dépend de l'importance du match (Coupe du Monde > amical).
  - Un multiplicateur de marge (margin-of-victory) évite que les gros scores
    gonflent artificiellement les notes (méthode FiveThirtyEight).

On convertit ensuite l'écart Elo en buts attendus (lambda) que l'on injecte
dans le moteur Poisson/Dixon-Coles existant : Elo et Poisson parlent enfin la
même langue.
"""
from math import log

RATING_INITIAL = 1500.0       # note de départ d'une équipe inconnue
HFA_DEFAULT = 65.0            # avantage du terrain en points Elo (~0.16 but)
ELO_PAR_BUT = 400.0          # 400 pts Elo ≈ 1 but de supériorité

# K-facteur par type de compétition (importance du match).
# Plus le match compte, plus la note bouge vite.
K_PAR_COMPETITION = {
    1: 60,    # Coupe du Monde
    4: 55,    # Euro
    9: 50,    # Copa América
    5: 45,    # Nations League
    29: 40, 30: 40, 31: 40, 32: 40, 33: 40, 34: 40,  # qualifs CDM
    10: 25,   # amicaux internationaux (comptent peu)
}
K_DEFAUT_CLUB = 30           # match de club standard


def expected_score(rating_a: float, rating_b: float, hfa: float = 0.0) -> float:
    """Probabilité (espérance de score) que A batte B. hfa = bonus terrain de A.

    E_A = 1 / (1 + 10^(-(R_A + hfa - R_B)/400))
    """
    return 1.0 / (1.0 + 10 ** (-(rating_a + hfa - rating_b) / 400.0))


def _mov_multiplier(diff_buts: int, diff_elo: float) -> float:
    """Multiplicateur de marge de victoire (méthode FiveThirtyEight).

    Une victoire 5-0 doit compter plus qu'un 1-0, mais pas linéairement, et
    on corrige l'auto-corrélation (les favoris gagnent souvent par gros score).
    """
    marge = abs(diff_buts)
    if marge <= 1:
        return 1.0
    return log(marge + 1.0) * (2.2 / (diff_elo * 0.001 + 2.2))


def maj_elo(
    rating_home: float,
    rating_away: float,
    buts_home: int,
    buts_away: int,
    k: float = K_DEFAUT_CLUB,
    hfa: float = HFA_DEFAULT,
) -> tuple[float, float]:
    """Met à jour les notes Elo des deux équipes après un match terminé."""
    e_home = expected_score(rating_home, rating_away, hfa)
    if buts_home > buts_away:
        s_home = 1.0
    elif buts_home == buts_away:
        s_home = 0.5
    else:
        s_home = 0.0

    diff_elo = (rating_home + hfa) - rating_away
    mult = _mov_multiplier(buts_home - buts_away, diff_elo if s_home == 1.0 else -diff_elo)

    delta = k * mult * (s_home - e_home)
    return rating_home + delta, rating_away - delta


def buts_attendus_elo(
    rating_home: float,
    rating_away: float,
    total_buts_ligue: float = 2.6,
    hfa: float = HFA_DEFAULT,
    terrain_neutre: bool = False,
) -> tuple[float, float]:
    """Convertit l'écart Elo en buts attendus (lambda) pour les deux équipes.

    supériorité = (R_home + hfa - R_away) / 400   (en buts)
    lam_home = total/2 + supériorité/2
    lam_away = total/2 - supériorité/2

    terrain_neutre : annule l'avantage du terrain (Coupe du Monde hors hôte).
    """
    bonus = 0.0 if terrain_neutre else hfa
    superiorite = (rating_home + bonus - rating_away) / ELO_PAR_BUT
    base = total_buts_ligue / 2.0
    lam_home = max(base + superiorite / 2.0, 0.15)
    lam_away = max(base - superiorite / 2.0, 0.15)
    return lam_home, lam_away


def proba_1x2_elo(rating_home: float, rating_away: float, hfa: float = HFA_DEFAULT,
                  terrain_neutre: bool = False) -> dict[str, float]:
    """Probabilités 1X2 dérivées de l'Elo via le moteur Poisson/Dixon-Coles."""
    from .poisson import compute_probabilities
    lam_h, lam_a = buts_attendus_elo(rating_home, rating_away, hfa=hfa,
                                     terrain_neutre=terrain_neutre)
    p = compute_probabilities(lam_h, lam_a)
    return {"1": p.home_win, "X": p.draw, "2": p.away_win}


# ============== Construction des ratings depuis l'historique ==============

def construire_ratings(fixtures_par_competition: list[tuple[int, list]]) -> dict[int, dict]:
    """Calcule une table Elo à partir d'un pool de matchs terminés.

    fixtures_par_competition : liste de (league_id, [fixtures de l'API]).
    Le league_id sert à choisir le K-facteur (importance de la compétition).

    On agrège TOUS les matchs, on les trie chronologiquement, puis on applique
    les mises à jour Elo dans l'ordre. Une équipe jamais vue démarre à 1500.
    Renvoie {team_id: {rating, nom, n_matchs}}.
    """
    # Aplatit en (date, league_id, match) puis trie par date croissante
    tous = []
    for league_id, fixtures in fixtures_par_competition:
        for f in fixtures:
            if f.get("fixture", {}).get("status", {}).get("short") not in (
                "FT", "AET", "PEN"
            ):
                continue
            gh = f.get("goals", {}).get("home")
            ga = f.get("goals", {}).get("away")
            if gh is None or ga is None:
                continue
            date = f.get("fixture", {}).get("date", "")
            tous.append((date, league_id, f))
    tous.sort(key=lambda x: x[0])

    ratings: dict[int, float] = {}
    noms: dict[int, str] = {}
    n_matchs: dict[int, int] = {}

    for _date, league_id, f in tous:
        home = f["teams"]["home"]
        away = f["teams"]["away"]
        hid, aid = home["id"], away["id"]
        noms[hid], noms[aid] = home["name"], away["name"]

        r_home = ratings.get(hid, RATING_INITIAL)
        r_away = ratings.get(aid, RATING_INITIAL)
        k = K_PAR_COMPETITION.get(league_id, K_DEFAUT_CLUB)

        # Sélections nationales : pas de vrai avantage terrain en compétition
        # neutre, mais l'historique mélange qualifs (à domicile) et phase finale.
        # On garde un HFA réduit pour le calcul des notes.
        hfa = HFA_DEFAULT if league_id not in K_PAR_COMPETITION else HFA_DEFAULT * 0.5

        nr_home, nr_away = maj_elo(
            r_home, r_away, int(f["goals"]["home"]), int(f["goals"]["away"]),
            k=k, hfa=hfa,
        )
        ratings[hid], ratings[aid] = nr_home, nr_away
        n_matchs[hid] = n_matchs.get(hid, 0) + 1
        n_matchs[aid] = n_matchs.get(aid, 0) + 1

    return {
        tid: {"rating": round(r, 1), "nom": noms.get(tid), "n_matchs": n_matchs.get(tid, 0)}
        for tid, r in ratings.items()
    }
