"""Moteur de probabilité par loi de Poisson + correction Dixon-Coles.

Idée : le nombre de buts d'une équipe sur un match suit approximativement
une loi de Poisson. Si on estime les buts attendus (lambda) de chaque équipe,
on peut calculer la probabilité de CHAQUE score exact, puis en déduire la
probabilité de tous les marchés : 1X2, Over/Under, BTTS, etc.

Amélioration Dixon-Coles (1997) : le Poisson indépendant sous-estime
systématiquement les scores faibles (0-0, 1-0, 0-1, 1-1). On applique une
correction τ(x,y) paramétrée par rho (≈ -0.13) qui redistribue de la masse
de probabilité vers ces scores — ce qui colle mieux à la réalité du foot.

Tout est transparent et auditable — aucune boîte noire.
"""
from dataclasses import dataclass
from math import exp, factorial

# Paramètre Dixon-Coles : valeur négative (plus de nuls/scores faibles que
# ne le prédit Poisson). -0.13 est la valeur typique trouvée sur données
# réelles (EPL 2017/18 : -0.1285). Voir Dixon & Coles 1997.
RHO_DIXON_COLES = -0.13


def poisson_pmf(k: int, lam: float) -> float:
    """Probabilité d'observer exactement k buts quand on en attend lam."""
    return (lam ** k) * exp(-lam) / factorial(k)


def tau_dixon_coles(hg: int, ag: int, lam: float, mu: float, rho: float) -> float:
    """Facteur correctif Dixon-Coles pour les 4 scores faibles.

    Ajuste la dépendance entre les buts des deux équipes que le Poisson
    indépendant ignore. Renvoie 1.0 pour tous les autres scores (aucun effet).

    lam = buts attendus domicile, mu = buts attendus extérieur.
    """
    if hg == 0 and ag == 0:
        return 1.0 - lam * mu * rho
    if hg == 0 and ag == 1:
        return 1.0 + lam * rho
    if hg == 1 and ag == 0:
        return 1.0 + mu * rho
    if hg == 1 and ag == 1:
        return 1.0 - rho
    return 1.0


@dataclass
class TeamStrength:
    """Force d'une équipe, mesurée par rapport à la moyenne du championnat.

    attack = (buts marqués par l'équipe) / (buts marqués en moyenne)
    defense = (buts encaissés par l'équipe) / (buts encaissés en moyenne)
    Un attack > 1 => attaque au-dessus de la moyenne.
    Un defense < 1 => défense au-dessus de la moyenne (encaisse peu).
    """
    attack: float
    defense: float


@dataclass
class MatchProbabilities:
    home_win: float
    draw: float
    away_win: float
    over_25: float
    under_25: float
    over_15: float
    under_15: float
    btts_yes: float   # les deux équipes marquent
    btts_no: float
    expected_home_goals: float
    expected_away_goals: float

    def as_dict(self) -> dict:
        return self.__dict__.copy()

    def as_market_dict(self) -> dict[str, float]:
        """Probabilités au même format de clés que le parser de cotes.

        Permet de comparer directement proba calculée vs cote du bookmaker.
        Inclut les doubles chances (1X, 12, X2).
        """
        return {
            "1": self.home_win,
            "X": self.draw,
            "2": self.away_win,
            "over_2.5": self.over_25,
            "under_2.5": self.under_25,
            "over_1.5": self.over_15,
            "under_1.5": self.under_15,
            "btts_oui": self.btts_yes,
            "btts_non": self.btts_no,
            "1X": self.home_win + self.draw,
            "12": self.home_win + self.away_win,
            "X2": self.draw + self.away_win,
        }


def expected_goals(
    home: TeamStrength,
    away: TeamStrength,
    league_avg_home_goals: float,
    league_avg_away_goals: float,
) -> tuple[float, float]:
    """Buts attendus pour chaque équipe.

    lambda_dom = force d'attaque domicile × faiblesse défense adverse × moyenne dom
    lambda_ext = force d'attaque extérieur × faiblesse défense adverse × moyenne ext
    """
    lam_home = home.attack * away.defense * league_avg_home_goals
    lam_away = away.attack * home.defense * league_avg_away_goals
    return lam_home, lam_away


def compute_probabilities(
    lam_home: float,
    lam_away: float,
    max_goals: int = 10,
    rho: float = RHO_DIXON_COLES,
) -> MatchProbabilities:
    """Construit la grille de tous les scores (corrigée Dixon-Coles) et agrège les marchés.

    rho : intensité de la correction Dixon-Coles. 0.0 = Poisson pur classique.
    """
    p_home = p_draw = p_away = 0.0
    p_over25 = p_over15 = p_btts = 0.0
    total = 0.0  # la correction DC casse légèrement la somme à 1 -> on renormalise

    for hg in range(max_goals + 1):
        for ag in range(max_goals + 1):
            p = poisson_pmf(hg, lam_home) * poisson_pmf(ag, lam_away)
            p *= tau_dixon_coles(hg, ag, lam_home, lam_away, rho)
            total += p

            if hg > ag:
                p_home += p
            elif hg == ag:
                p_draw += p
            else:
                p_away += p

            if hg + ag > 2.5:
                p_over25 += p
            if hg + ag > 1.5:
                p_over15 += p
            if hg >= 1 and ag >= 1:
                p_btts += p

    # Renormalisation (la correction τ modifie légèrement la masse totale)
    if total > 0:
        p_home, p_draw, p_away = p_home / total, p_draw / total, p_away / total
        p_over25, p_over15, p_btts = p_over25 / total, p_over15 / total, p_btts / total

    return MatchProbabilities(
        home_win=p_home,
        draw=p_draw,
        away_win=p_away,
        over_25=p_over25,
        under_25=1 - p_over25,
        over_15=p_over15,
        under_15=1 - p_over15,
        btts_yes=p_btts,
        btts_no=1 - p_btts,
        expected_home_goals=lam_home,
        expected_away_goals=lam_away,
    )


def analyser_match(
    home: TeamStrength,
    away: TeamStrength,
    league_avg_home_goals: float = 1.5,
    league_avg_away_goals: float = 1.1,
) -> MatchProbabilities:
    """Point d'entrée : forces d'équipes -> probabilités de tous les marchés."""
    lam_home, lam_away = expected_goals(
        home, away, league_avg_home_goals, league_avg_away_goals
    )
    return compute_probabilities(lam_home, lam_away)
