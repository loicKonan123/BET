"""Moteur de probabilité par loi de Poisson (100% statistique, zéro ML).

Idée : le nombre de buts d'une équipe sur un match suit approximativement
une loi de Poisson. Si on estime les buts attendus (lambda) de chaque équipe,
on peut calculer la probabilité de CHAQUE score exact, puis en déduire la
probabilité de tous les marchés : 1X2, Over/Under, BTTS, etc.

Tout est transparent et auditable — aucune boîte noire.
"""
from dataclasses import dataclass
from math import exp, factorial


def poisson_pmf(k: int, lam: float) -> float:
    """Probabilité d'observer exactement k buts quand on en attend lam."""
    return (lam ** k) * exp(-lam) / factorial(k)


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
) -> MatchProbabilities:
    """Construit la grille de tous les scores possibles et agrège les marchés."""
    p_home = p_draw = p_away = 0.0
    p_over = p_btts = 0.0

    for hg in range(max_goals + 1):
        for ag in range(max_goals + 1):
            p = poisson_pmf(hg, lam_home) * poisson_pmf(ag, lam_away)

            if hg > ag:
                p_home += p
            elif hg == ag:
                p_draw += p
            else:
                p_away += p

            if hg + ag > 2.5:
                p_over += p
            if hg >= 1 and ag >= 1:
                p_btts += p

    return MatchProbabilities(
        home_win=p_home,
        draw=p_draw,
        away_win=p_away,
        over_25=p_over,
        under_25=1 - p_over,
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
