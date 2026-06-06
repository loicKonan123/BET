"""Récupère les stats d'une équipe et en déduit ses buts attendus (lambda).

On utilise l'endpoint `teams/statistics` d'API-Football qui donne, pour une
équipe sur une saison/ligue, ses moyennes de buts marqués et encaissés,
séparées domicile / extérieur.

Modèle de buts attendus (simple, robuste, ne nécessite QUE les 2 équipes) :
    lambda_dom = (buts marqués/match de l'équipe DOM à domicile
                  + buts encaissés/match de l'équipe EXT à l'extérieur) / 2
    lambda_ext = (buts marqués/match de l'équipe EXT à l'extérieur
                  + buts encaissés/match de l'équipe DOM à domicile) / 2

C'est la force d'attaque d'un côté croisée avec la faiblesse défensive de
l'autre. Transparent et économe en requêtes API.
"""
from dataclasses import dataclass

from .api_client import ApiFootball


@dataclass
class StatsEquipe:
    nom: str
    matchs_joues: int
    buts_marques_dom: float   # moyenne / match à domicile
    buts_marques_ext: float   # moyenne / match à l'extérieur
    buts_encaisses_dom: float
    buts_encaisses_ext: float
    forme: str                # ex "WWDLW"

    @property
    def fiable(self) -> bool:
        """Assez de matchs pour que les moyennes soient significatives ?"""
        return self.matchs_joues >= 5


def _f(x, defaut: float = 0.0) -> float:
    """Convertit en float en gérant None / chaîne vide."""
    try:
        return float(x)
    except (TypeError, ValueError):
        return defaut


def parser_stats(resp: dict) -> StatsEquipe:
    """Transforme la réponse brute teams/statistics en StatsEquipe."""
    goals = resp.get("goals", {})
    avg_for = goals.get("for", {}).get("average", {})
    avg_against = goals.get("against", {}).get("average", {})
    played = resp.get("fixtures", {}).get("played", {})

    return StatsEquipe(
        nom=resp.get("team", {}).get("name", "?"),
        matchs_joues=int(played.get("total", 0) or 0),
        buts_marques_dom=_f(avg_for.get("home")),
        buts_marques_ext=_f(avg_for.get("away")),
        buts_encaisses_dom=_f(avg_against.get("home")),
        buts_encaisses_ext=_f(avg_against.get("away")),
        forme=resp.get("form", "") or "",
    )


def recuperer_stats(api: ApiFootball, league: int, season: int, team: int) -> StatsEquipe | None:
    """Appelle l'API (1 requête) et renvoie les stats parsées, ou None si vide."""
    data = api.get("teams/statistics", {"league": league, "season": season, "team": team})
    resp = data.get("response")
    if not resp:
        return None
    return parser_stats(resp)


def parser_stats_national(fixtures: list, team_id: int) -> StatsEquipe | None:
    """Calcule la force d'une sélection nationale à partir de ses matchs.

    Pour une nation (Coupe du Monde), les stats « saison de ligue » n'existent
    pas vraiment. On prend tous ses matchs internationaux terminés de la saison
    et on en tire les moyennes buts marqués / encaissés.

    En Coupe du Monde les terrains sont neutres -> on met la même valeur en
    domicile et extérieur (moyenne globale), pour réutiliser `buts_attendus`.
    Les fixtures arrivent du plus ancien au plus récent -> la forme prend les 5 derniers.
    """
    marques, encaisses, forme = [], [], []
    nom = "?"

    for f in fixtures:
        if f.get("fixture", {}).get("status", {}).get("short") != "FT":
            continue
        home = f["teams"]["home"]
        away = f["teams"]["away"]
        gh = f.get("goals", {}).get("home")
        ga = f.get("goals", {}).get("away")
        if gh is None or ga is None:
            continue

        if home["id"] == team_id:
            nom, gf, gc = home["name"], gh, ga
        elif away["id"] == team_id:
            nom, gf, gc = away["name"], ga, gh
        else:
            continue

        marques.append(gf)
        encaisses.append(gc)
        forme.append("W" if gf > gc else ("D" if gf == gc else "L"))

    if not marques:
        return None

    avg_marques = sum(marques) / len(marques)
    avg_encaisses = sum(encaisses) / len(encaisses)
    return StatsEquipe(
        nom=nom,
        matchs_joues=len(marques),
        buts_marques_dom=avg_marques,
        buts_marques_ext=avg_marques,
        buts_encaisses_dom=avg_encaisses,
        buts_encaisses_ext=avg_encaisses,
        forme="".join(forme[-5:]),  # 5 derniers, plus récent à droite
    )


def recuperer_stats_national(api: ApiFootball, team: int, derniers: int = 20) -> StatsEquipe | None:
    """Appelle l'API (1 requête) : N derniers matchs d'une sélection -> StatsEquipe.

    Le paramètre `last` est réservé aux plans payants (PRO). Donne la forme
    internationale la plus à jour (qualifs, Nations League, amicaux).
    """
    data = api.get("fixtures", {"team": team, "last": derniers})
    return parser_stats_national(data.get("response", []), team)


def buts_attendus(dom: StatsEquipe, ext: StatsEquipe) -> tuple[float, float]:
    """Calcule (lambda_domicile, lambda_extérieur) à partir des 2 équipes."""
    lam_dom = (dom.buts_marques_dom + ext.buts_encaisses_ext) / 2
    lam_ext = (ext.buts_marques_ext + dom.buts_encaisses_dom) / 2
    # garde-fou : jamais 0 (sinon Poisson dégénère), borne basse réaliste
    lam_dom = max(lam_dom, 0.15)
    lam_ext = max(lam_ext, 0.15)
    return lam_dom, lam_ext
