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
from datetime import datetime, timezone
from math import exp

from .api_client import ApiFootball

# Pondération temporelle (Dixon-Coles time-decay) : un match d'il y a N jours
# pèse exp(-XI_DECAY * N). XI ≈ 0.003/jour => demi-vie ~230 jours (~8 mois).
# Adapté aux sélections nationales qui jouent peu et évoluent lentement mais
# dont la forme récente reste plus informative que les matchs anciens.
XI_DECAY = 0.003


def _poids_temporel(date_iso: str, ref: datetime | None = None) -> float:
    """Poids exponentiel décroissant selon l'ancienneté du match (jours)."""
    if not date_iso:
        return 1.0
    try:
        d = datetime.fromisoformat(date_iso.replace("Z", "+00:00"))
    except ValueError:
        return 1.0
    ref = ref or datetime.now(timezone.utc)
    jours = max((ref - d).days, 0)
    return exp(-XI_DECAY * jours)


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

    Utilise les stats dom/ext séparées (même en WC, l'historique dom/ext
    reflète mieux la force réelle : les hôtes performent mieux à domicile,
    les équipes déplacées moins bien en déplacement).
    Les fixtures arrivent du plus ancien au plus récent -> la forme prend les 5 derniers.
    """
    # chaque entrée = (buts, poids_temporel)
    home_scored, home_conceded = [], []
    away_scored, away_conceded = [], []
    all_scored, all_conceded, forme = [], [], []
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

        poids = _poids_temporel(f.get("fixture", {}).get("date", ""))

        if home["id"] == team_id:
            nom, gf, gc = home["name"], gh, ga
            home_scored.append((gf, poids))
            home_conceded.append((gc, poids))
        elif away["id"] == team_id:
            nom, gf, gc = away["name"], ga, gh
            away_scored.append((gf, poids))
            away_conceded.append((gc, poids))
        else:
            continue

        all_scored.append((gf, poids))
        all_conceded.append((gc, poids))
        forme.append("W" if gf > gc else ("D" if gf == gc else "L"))

    if not all_scored:
        return None

    def _moy_ponderee(paires, fallback=None):
        """Moyenne pondérée par le poids temporel. fallback si liste vide."""
        if not paires:
            return fallback
        num = sum(v * w for v, w in paires)
        den = sum(w for _, w in paires)
        return num / den if den > 0 else fallback

    avg_all = _moy_ponderee(all_scored)
    avg_enc_all = _moy_ponderee(all_conceded)

    return StatsEquipe(
        nom=nom,
        matchs_joues=len(all_scored),
        buts_marques_dom=_moy_ponderee(home_scored, avg_all),
        buts_marques_ext=_moy_ponderee(away_scored, avg_all),
        buts_encaisses_dom=_moy_ponderee(home_conceded, avg_enc_all),
        buts_encaisses_ext=_moy_ponderee(away_conceded, avg_enc_all),
        forme="".join(forme[-5:]),
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
