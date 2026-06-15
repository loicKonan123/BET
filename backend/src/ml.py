"""4e coéquipier : modèle ML (gradient boosting) sur features enrichies xG.

L'apport décisif vs Elo/Poisson : le **xG** (expected goals) mesure la QUALITÉ
de jeu indépendamment du résultat — une équipe peut gagner avec un faible xG
(chance) ou perdre avec un fort xG. Le xG glissant prédit mieux le futur que les
seuls scores. C'est le signal que les autres modèles ne captent pas.

Features (toutes PRÉ-MATCH, anti-fuite) :
  - écart Elo, Elo dom/ext
  - xG glissant créé/concédé (dom et ext), différentiels xG croisés
  - forme buts marqués/encaissés glissante

Le modèle est un HistGradientBoostingClassifier (scikit-learn, aucune dépendance
nouvelle) calibré par régression isotonique. Entraîné par ligue sur l'historique
en cache, validé en walk-forward, il s'ajoute au consensus comme 4e source.

Validé (EPL 2023+2024, walk-forward) : log-loss 0.995 vs 1.006 pour l'Elo seul.
"""
from collections import defaultdict, deque
from datetime import datetime

import numpy as np

from .elo import RATING_INITIAL, K_DEFAUT_CLUB, HFA_DEFAULT, maj_elo

K_FENETRE = 6      # taille de la fenêtre glissante
MIN_HIST = 4       # min de matchs passés par équipe pour une prédiction fiable

FEATURES = [
    "elo_diff", "elo_home", "elo_away",
    "xgf_h", "xga_h", "xgf_a", "xga_a", "xg_diff_h", "xg_diff_a",
    "gf_h", "ga_h", "gf_a", "ga_a",
]


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def extraire_xg(stats_resp: list) -> dict[int, tuple[float, float] | None]:
    """De la réponse fixtures/statistics -> {team_id: (xg, _) } (xg seul utilisé)."""
    out: dict[int, float | None] = {}
    for t in stats_resp or []:
        tid = t.get("team", {}).get("id")
        s = {x.get("type"): x.get("value") for x in t.get("statistics", [])}
        out[tid] = _num(s.get("expected_goals"))
    return out


class _Etat:
    __slots__ = ("elo", "form", "xg")

    def __init__(self):
        self.elo = RATING_INITIAL
        self.form = deque(maxlen=K_FENETRE)   # (gf, ga)
        self.xg = deque(maxlen=K_FENETRE)     # (xg_for, xg_against)


def _feat(eh: _Etat, ea: _Etat) -> list[float]:
    xgf_h = np.mean([x[0] for x in eh.xg]) if eh.xg else 1.2
    xga_h = np.mean([x[1] for x in eh.xg]) if eh.xg else 1.2
    xgf_a = np.mean([x[0] for x in ea.xg]) if ea.xg else 1.2
    xga_a = np.mean([x[1] for x in ea.xg]) if ea.xg else 1.2
    gff_h = np.mean([x[0] for x in eh.form]) if eh.form else 1.2
    gfa_h = np.mean([x[1] for x in eh.form]) if eh.form else 1.2
    gff_a = np.mean([x[0] for x in ea.form]) if ea.form else 1.2
    gfa_a = np.mean([x[1] for x in ea.form]) if ea.form else 1.2
    return [
        (eh.elo + HFA_DEFAULT) - ea.elo, eh.elo, ea.elo,
        xgf_h, xga_h, xgf_a, xga_a, xgf_h - xga_a, xgf_a - xga_h,
        gff_h, gfa_h, gff_a, gfa_a,
    ]


def _rejouer(fixtures: list, xg_par_fixture: dict[int, dict]) -> tuple[dict[int, _Etat], list, list, list]:
    """Rejoue les matchs chronologiquement.

    Renvoie (etats_finaux, X, y, dates) — etats_finaux sert à prédire les
    matchs à venir (état le plus récent de chaque équipe).
    """
    rows = [f for f in fixtures
            if f.get("fixture", {}).get("status", {}).get("short") in ("FT", "AET", "PEN")
            and f.get("goals", {}).get("home") is not None
            and f.get("goals", {}).get("away") is not None]
    rows.sort(key=lambda f: f.get("fixture", {}).get("date", ""))

    etats: dict[int, _Etat] = defaultdict(_Etat)
    X, y, dates = [], [], []

    for f in rows:
        h = f["teams"]["home"]["id"]
        a = f["teams"]["away"]["id"]
        gh, ga = int(f["goals"]["home"]), int(f["goals"]["away"])
        eh, ea = etats[h], etats[a]

        if len(eh.form) >= MIN_HIST and len(ea.form) >= MIN_HIST:
            X.append(_feat(eh, ea))
            y.append(0 if gh > ga else (1 if gh == ga else 2))
            dates.append(f.get("fixture", {}).get("date", ""))

        # mise à jour APRÈS génération (anti-fuite)
        eh.form.append((gh, ga))
        ea.form.append((ga, gh))
        xgm = xg_par_fixture.get(f["fixture"]["id"], {})
        xh, xa = xgm.get(h), xgm.get(a)
        if xh is not None and xa is not None:
            eh.xg.append((xh, xa))
            ea.xg.append((xa, xh))
        eh.elo, ea.elo = maj_elo(eh.elo, ea.elo, gh, ga, k=K_DEFAUT_CLUB)

    return etats, X, y, dates


class ModeleML:
    """Modèle entraîné + états récents des équipes, pour prédire un match à venir."""

    def __init__(self, clf, etats: dict[int, _Etat]):
        self.clf = clf
        self.etats = etats

    def connait(self, team_id: int) -> bool:
        e = self.etats.get(team_id)
        return e is not None and len(e.form) >= MIN_HIST

    def proba_1x2(self, home_id: int, away_id: int) -> dict[str, float] | None:
        if not self.connait(home_id) or not self.connait(away_id):
            return None
        x = np.array([_feat(self.etats[home_id], self.etats[away_id])])
        p = self.clf.predict_proba(x)[0]
        return {"1": float(p[0]), "X": float(p[1]), "2": float(p[2])}


def _metriques(P, y) -> dict:
    """Log-loss, Brier, accuracy et courbe de calibration pour des probas (n,3)."""
    from math import log
    n = len(y)
    ll = sum(-log(max(P[i][y[i]], 1e-12)) for i in range(n)) / n
    br = sum(sum((P[i][k] - (1.0 if k == y[i] else 0.0)) ** 2 for k in range(3))
             for i in range(n)) / n
    ok = sum(1 for i in range(n) if max(range(3), key=lambda k: P[i][k]) == y[i])
    # Calibration : bins sur la proba du favori
    bins = {b: {"n": 0, "ok": 0, "somme": 0.0} for b in range(10)}
    for i in range(n):
        pred = max(range(3), key=lambda k: P[i][k])
        pf = P[i][pred]
        b = min(int(pf * 10), 9)
        bins[b]["n"] += 1
        bins[b]["somme"] += pf
        bins[b]["ok"] += int(pred == y[i])
    calibration = [
        {"bin": f"{b*10}-{b*10+10}%",
         "proba_moyenne": round(bins[b]["somme"] / bins[b]["n"] * 100, 1),
         "reussite_reelle": round(bins[b]["ok"] / bins[b]["n"] * 100, 1),
         "n": bins[b]["n"]}
        for b in range(10) if bins[b]["n"] > 0
    ]
    return {"n": n, "log_loss": round(ll, 4), "brier_score": round(br, 4),
            "accuracy_1x2": round(ok / n * 100, 1), "calibration": calibration}


def evaluer_ml(fixtures: list, xg_par_fixture: dict[int, dict],
               frac_train: float = 0.7, min_lignes: int = 150) -> dict | None:
    """Étude walk-forward du modèle ML : ML vs Elo + importance des features.

    Entraîne sur les `frac_train` premiers matchs (chronologiquement), évalue sur
    le reste (jamais vu). Compare au baseline Elo et calcule l'importance de
    chaque feature (permutation). Sert à la page « Étude du modèle ».
    """
    import numpy as np
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.inspection import permutation_importance

    from .elo import proba_1x2_elo

    _etats, X, y, dates = _rejouer(fixtures, xg_par_fixture)
    if len(y) < min_lignes or len(set(y)) < 3:
        return None

    X = np.array(X)
    y = np.array(y)
    ordre = np.argsort(dates)
    X, y = X[ordre], y[ordre]
    cut = int(len(y) * frac_train)
    Xtr, Xte, ytr, yte = X[:cut], X[cut:], y[:cut], y[cut:]
    if len(yte) < 30 or len(set(ytr)) < 3:
        return None

    clf = CalibratedClassifierCV(
        HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, max_depth=4,
                                       l2_regularization=1.0, random_state=0),
        method="isotonic", cv=3)
    clf.fit(Xtr, ytr)
    P_ml = clf.predict_proba(Xte)

    # Baseline Elo (colonnes 1 = elo_home, 2 = elo_away)
    P_elo = []
    for i in range(len(yte)):
        p = proba_1x2_elo(float(Xte[i][1]), float(Xte[i][2]))
        P_elo.append([p["1"], p["X"], p["2"]])

    # Importance des features (permutation, score = -log-loss)
    try:
        imp = permutation_importance(clf, Xte, yte, scoring="neg_log_loss",
                                     n_repeats=5, random_state=0)
        importance = sorted(
            [{"feature": FEATURES[i], "poids": round(float(imp.importances_mean[i]), 4)}
             for i in range(len(FEATURES))],
            key=lambda d: -d["poids"])
    except Exception:
        importance = []

    return {
        "n_train": cut,
        "n_test": len(yte),
        "ml": _metriques(P_ml, yte),
        "elo": _metriques(P_elo, yte),
        "importance": importance,
    }


def entrainer(fixtures: list, xg_par_fixture: dict[int, dict],
              min_lignes: int = 200) -> ModeleML | None:
    """Entraîne le modèle ML (GBM calibré) sur l'historique d'une ligue."""
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.ensemble import HistGradientBoostingClassifier

    etats, X, y, _dates = _rejouer(fixtures, xg_par_fixture)
    if len(y) < min_lignes or len(set(y)) < 3:
        return None

    base = HistGradientBoostingClassifier(
        max_iter=300, learning_rate=0.05, max_depth=4,
        l2_regularization=1.0, random_state=0,
    )
    clf = CalibratedClassifierCV(base, method="isotonic", cv=3)
    clf.fit(np.array(X), np.array(y))
    return ModeleML(clf, etats)
