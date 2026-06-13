"""Estimation des forces attaque/défense par maximum de vraisemblance (vrai Dixon-Coles).

Les moyennes de buts brutes (team_stats) ont un défaut majeur : elles ne corrigent
pas la QUALITÉ des adversaires rencontrés. Marquer 2 buts/match contre les pires
défenses ne vaut pas 2 buts/match contre les meilleures — c'est le biais de force
de calendrier (le bug Mexico/RSA).

Le vrai modèle Dixon-Coles (1997) le règle à la racine : on estime SIMULTANÉMENT,
pour chaque équipe i, un paramètre d'attaque α_i et de défense β_i, plus un
avantage du terrain γ global. Les buts attendus sont log-linéaires :

    λ_dom = exp(c + γ + α_dom − β_ext)
    λ_ext = exp(c + α_ext − β_dom)

Tous les paramètres sont ajustés ensemble en maximisant la log-vraisemblance de
Poisson — corrigée Dixon-Coles sur les scores faibles (τ, rho) et pondérée dans
le temps (les matchs récents pèsent plus). Une régularisation L2 fait du
shrinkage : les équipes peu vues sont tirées vers la moyenne (empirical Bayes).

Résultat : la force d'une équipe est démêlée de celle de ses adversaires. C'est
la même mécanique que les notes de référence (FiveThirtyEight SPI, Opta).
"""
from datetime import datetime, timezone

import numpy as np
from scipy.optimize import minimize

from .poisson import RHO_DIXON_COLES, compute_probabilities

XI_DECAY = 0.003   # demi-vie ~230 j (cohérent avec team_stats)
REG_L2 = 0.05      # régularisation -> shrinkage des équipes peu vues
EPS = 1e-9


def _jours_depuis(date_iso: str, ref: datetime) -> float:
    try:
        d = datetime.fromisoformat(date_iso.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return 0.0
    return max((ref - d).days, 0)


class ModeleDixonColes:
    """Modèle ajusté : convertit (équipe dom, équipe ext) -> buts attendus / probas."""

    def __init__(self, index: dict[int, int], attaque: np.ndarray, defense: np.ndarray,
                 intercept: float, home_adv: float, noms: dict[int, str],
                 rho: float = RHO_DIXON_COLES):
        self.index = index          # team_id -> position dans les vecteurs
        self.attaque = attaque
        self.defense = defense
        self.intercept = intercept
        self.home_adv = home_adv
        self.noms = noms
        self.rho = rho
        # Force « moyenne » pour les équipes inconnues (shrinkage = 0)
        self._att_moy = float(np.mean(attaque)) if len(attaque) else 0.0
        self._def_moy = float(np.mean(defense)) if len(defense) else 0.0

    def connait(self, team_id: int) -> bool:
        return team_id in self.index

    def _ab(self, team_id: int) -> tuple[float, float]:
        i = self.index.get(team_id)
        if i is None:
            return self._att_moy, self._def_moy
        return float(self.attaque[i]), float(self.defense[i])

    def buts_attendus(self, home_id: int, away_id: int,
                      terrain_neutre: bool = False) -> tuple[float, float]:
        a_h, d_h = self._ab(home_id)
        a_a, d_a = self._ab(away_id)
        gamma = 0.0 if terrain_neutre else self.home_adv
        lam_h = np.exp(self.intercept + gamma + a_h - d_a)
        lam_a = np.exp(self.intercept + a_a - d_h)
        return max(float(lam_h), 0.15), max(float(lam_a), 0.15)

    def proba_1x2(self, home_id: int, away_id: int,
                  terrain_neutre: bool = False) -> dict[str, float]:
        lam_h, lam_a = self.buts_attendus(home_id, away_id, terrain_neutre)
        p = compute_probabilities(lam_h, lam_a, rho=self.rho)
        return {"1": p.home_win, "X": p.draw, "2": p.away_win}


def _parser_matchs(fixtures: list, ref: datetime, xi: float):
    """Extrait (idx_dom, idx_ext, buts_dom, buts_ext, poids) + index/noms."""
    index: dict[int, int] = {}
    noms: dict[int, str] = {}

    def idx(team: dict) -> int:
        tid = team["id"]
        if tid not in index:
            index[tid] = len(index)
            noms[tid] = team.get("name", "?")
        return index[tid]

    hi, ai, gh, ga, w = [], [], [], [], []
    for f in fixtures:
        if f.get("fixture", {}).get("status", {}).get("short") not in ("FT", "AET", "PEN"):
            continue
        g_h = f.get("goals", {}).get("home")
        g_a = f.get("goals", {}).get("away")
        if g_h is None or g_a is None:
            continue
        hi.append(idx(f["teams"]["home"]))
        ai.append(idx(f["teams"]["away"]))
        gh.append(int(g_h))
        ga.append(int(g_a))
        jours = _jours_depuis(f.get("fixture", {}).get("date", ""), ref)
        w.append(np.exp(-xi * jours))

    return (index, noms,
            np.array(hi), np.array(ai),
            np.array(gh, dtype=float), np.array(ga, dtype=float),
            np.array(w))


def _tau_vectorise(gh: np.ndarray, ga: np.ndarray,
                   lam: np.ndarray, mu: np.ndarray, rho: float) -> np.ndarray:
    """Facteur Dixon-Coles τ appliqué en masse sur les 4 scores faibles."""
    tau = np.ones_like(lam)
    m00 = (gh == 0) & (ga == 0)
    m01 = (gh == 0) & (ga == 1)
    m10 = (gh == 1) & (ga == 0)
    m11 = (gh == 1) & (ga == 1)
    tau[m00] = 1.0 - lam[m00] * mu[m00] * rho
    tau[m01] = 1.0 + lam[m01] * rho
    tau[m10] = 1.0 + mu[m10] * rho
    tau[m11] = 1.0 - rho
    return np.maximum(tau, EPS)


def ajuster(fixtures: list, ref_date: datetime | None = None,
            xi: float = XI_DECAY, reg: float = REG_L2,
            rho: float = RHO_DIXON_COLES, min_matchs: int = 30) -> ModeleDixonColes | None:
    """Ajuste les forces attaque/défense par MLE sur un pool de matchs terminés.

    Renvoie None si trop peu de matchs pour une estimation fiable.
    """
    ref = ref_date or datetime.now(timezone.utc)
    index, noms, hi, ai, gh, ga, w = _parser_matchs(fixtures, ref, xi)
    n = len(index)
    if len(hi) < min_matchs or n < 4:
        return None

    # params = [attaque(n), defense(n), intercept, home_adv]
    def depack(p):
        return p[:n], p[n:2 * n], p[2 * n], p[2 * n + 1]

    def nll(p):
        att, dfn, c, hadv = depack(p)
        lam = np.exp(c + hadv + att[hi] - dfn[ai])
        mu = np.exp(c + att[ai] - dfn[hi])
        tau = _tau_vectorise(gh, ga, lam, mu, rho)
        # log-vraisemblance Poisson (terme factoriel constant ignoré) + correction τ
        ll = w * (gh * np.log(lam) - lam + ga * np.log(mu) - mu + np.log(tau))
        # L2 -> shrinkage vers 0 (= force moyenne) pour les équipes peu vues
        penalite = reg * (np.sum(att ** 2) + np.sum(dfn ** 2))
        return -np.sum(ll) + penalite

    # Init : tout à 0 (force moyenne), intercept ~ log(buts moyens), HFA léger
    p0 = np.zeros(2 * n + 2)
    p0[2 * n] = np.log(max((gh.mean() + ga.mean()) / 2.0, 0.3))
    p0[2 * n + 1] = 0.25

    res = minimize(nll, p0, method="L-BFGS-B",
                   options={"maxiter": 400, "ftol": 1e-9})
    if not res.success and res.status not in (0, 1, 2):
        return None

    att, dfn, c, hadv = depack(res.x)
    # Centrage (identifiabilité) : moyenne d'attaque/défense = 0, le reste va dans l'intercept
    att = att - att.mean()
    dfn = dfn - dfn.mean()
    return ModeleDixonColes(index, att, dfn, float(c), float(hadv), noms, rho)
