"""Backtest : rejoue le modèle Poisson sur les matchs terminés d'une saison.

Coût API (première exécution) :
  - 1 appel  : tous les fixtures de la saison (mis en cache)
  - N appels : stats de chaque équipe unique (N ≈ 20 pour une ligue normale)
Exécutions suivantes : 0 appel (tout en cache disque).
"""
from math import log

from .api_client import ApiFootball
from .pipeline import (
    FixtureInfo,
    STATUTS_TERMINES,
    analyser_fixture_sans_cotes,
    _nom_ligue,
)


def _brier_1x2(probas: dict, reel: str) -> float:
    """Brier score multi-classe pour le 1X2 (0 = parfait, 2 = pire).

    Σ (proba_k - issue_k)²  sur les 3 issues {1, X, 2}.
    Mesure la CALIBRATION : récompense les probas honnêtes, pas juste le bon pari.
    """
    s = 0.0
    for k in ("1", "X", "2"):
        issue = 1.0 if k == reel else 0.0
        s += (probas.get(k, 0.0) - issue) ** 2
    return s


def _logloss_1x2(probas: dict, reel: str) -> float:
    """Log-loss (ignorance score) sur l'issue réelle 1X2.

    -log(proba assignée à l'issue qui s'est produite). Plus c'est bas, mieux
    c'est. Pénalise très fort la confiance mal placée. Recommandé par la
    littérature (Constantinou & Fenton) au-dessus du RPS.
    """
    p = max(probas.get(reel, 0.0), 1e-12)  # garde-fou log(0)
    return -log(p)


def _resultat_reel(score_home: int, score_away: int) -> dict:
    total = score_home + score_away
    if score_home > score_away:
        r1x2 = "1"
    elif score_home == score_away:
        r1x2 = "X"
    else:
        r1x2 = "2"
    return {
        "1x2": r1x2,
        "over_2.5": "over_2.5" if total > 2.5 else "under_2.5",
        "btts": "btts_oui" if score_home > 0 and score_away > 0 else "btts_non",
    }


def run_backtest(
    api: ApiFootball,
    league_id: int,
    season: int,
    limit: int | None = None,
) -> dict:
    """Rejoue le modèle sur les matchs terminés de (league_id, season).

    limit : si fourni, ne prend que les `limit` matchs les plus récents.
    """
    # 1 — Récupère tous les fixtures de la saison (1 appel, mis en cache)
    data = api.get("fixtures", {"league": league_id, "season": season})
    reponse = data.get("response", [])

    fixtures: list[FixtureInfo] = []
    scores: dict[int, tuple[int, int]] = {}

    for f in reponse:
        status = f["fixture"]["status"]["short"]
        if status not in STATUTS_TERMINES:
            continue
        gh = f["goals"]["home"]
        ga = f["goals"]["away"]
        if gh is None or ga is None:
            continue
        fid = f["fixture"]["id"]
        scores[fid] = (int(gh), int(ga))
        fixtures.append(FixtureInfo(
            fixture_id=fid,
            league=f["league"]["id"],
            season=f["league"]["season"],
            home_id=f["teams"]["home"]["id"],
            away_id=f["teams"]["away"]["id"],
            home_name=f["teams"]["home"]["name"],
            away_name=f["teams"]["away"]["name"],
            date=f["fixture"].get("date", ""),
            status=status,
        ))

    # Trie par date croissante, garde les plus récents si limite
    fixtures.sort(key=lambda x: x.date)
    if limit:
        fixtures = fixtures[-limit:]

    # 2 — Rejoue le modèle sur chaque match et compare au résultat réel
    resultats = []

    # Compteurs séparés par direction (prédit X → était-ce X ?)
    c: dict[str, int] = {
        "ok_1x2": 0, "total_1x2": 0,
        "ok_over25": 0,  "n_over25": 0,   # quand modèle prédit "plus de 2.5"
        "ok_under25": 0, "n_under25": 0,  # quand modèle prédit "moins de 2.5"
        "ok_over15": 0,  "n_over15": 0,
        "ok_under15": 0, "n_under15": 0,
        "ok_btts_oui": 0, "n_btts_oui": 0,
        "ok_btts_non": 0, "n_btts_non": 0,
        "ok_dc_12": 0, "n_dc_12": 0,
        "ok_dc_1x": 0, "n_dc_1x": 0,
    }

    # Calibration : on cumule Brier + log-loss sur le 1X2
    somme_brier = 0.0
    somme_logloss = 0.0
    # Bins de calibration : proba prédite (favori) vs taux de réussite réel
    cal_bins = {i: {"n": 0, "ok": 0, "somme_proba": 0.0} for i in range(10)}

    for fx in fixtures:
        analyse = analyser_fixture_sans_cotes(api, fx, stats_season=season)
        if not analyse:
            continue

        score_home, score_away = scores[fx.fixture_id]
        reel = _resultat_reel(score_home, score_away)
        probas = analyse["probabilites"]
        total_buts = score_home + score_away

        # Calibration 1X2
        somme_brier += _brier_1x2(probas, reel["1x2"])
        somme_logloss += _logloss_1x2(probas, reel["1x2"])
        p_favori = max(probas.get("1", 0), probas.get("X", 0), probas.get("2", 0))
        bin_idx = min(int(p_favori * 10), 9)
        cal_bins[bin_idx]["n"] += 1
        cal_bins[bin_idx]["somme_proba"] += p_favori
        if max(["1", "X", "2"], key=lambda k: probas.get(k, 0)) == reel["1x2"]:
            cal_bins[bin_idx]["ok"] += 1

        pred_1x2    = max(["1", "X", "2"], key=lambda k: probas.get(k, 0))
        pred_over25 = "over_2.5"  if probas.get("over_2.5", 0) >= 0.5 else "under_2.5"
        pred_over15 = "over_1.5"  if probas.get("over_1.5", 0) >= 0.5 else "under_1.5"
        pred_btts   = "btts_oui"  if probas.get("btts_oui", 0) >= 0.5 else "btts_non"
        pred_dc_12  = "12"        if probas.get("12", 0)        >= 0.5 else "nul_possible"
        pred_dc_1x  = "1X"        if probas.get("1X", 0)        >= 0.5 else "ext_gagne"

        reel_over15 = "over_1.5"      if total_buts > 1.5  else "under_1.5"
        reel_dc_12  = "12"            if reel["1x2"] in ("1", "2") else "nul_possible"
        reel_dc_1x  = "1X"            if reel["1x2"] in ("1", "X") else "ext_gagne"

        bon_1x2    = pred_1x2    == reel["1x2"]
        bon_over25 = pred_over25 == reel["over_2.5"]
        bon_over15 = pred_over15 == reel_over15
        bon_btts   = pred_btts   == reel["btts"]
        bon_dc_12  = pred_dc_12  == reel_dc_12
        bon_dc_1x  = pred_dc_1x  == reel_dc_1x

        # 1X2
        c["ok_1x2"] += int(bon_1x2); c["total_1x2"] += 1

        # Over/Under 2.5 — séparés par direction
        if pred_over25 == "over_2.5":
            c["n_over25"] += 1; c["ok_over25"] += int(bon_over25)
        else:
            c["n_under25"] += 1; c["ok_under25"] += int(bon_over25)

        # Over/Under 1.5 — séparés par direction
        if pred_over15 == "over_1.5":
            c["n_over15"] += 1; c["ok_over15"] += int(bon_over15)
        else:
            c["n_under15"] += 1; c["ok_under15"] += int(bon_over15)

        # BTTS — séparés par direction
        if pred_btts == "btts_oui":
            c["n_btts_oui"] += 1; c["ok_btts_oui"] += int(bon_btts)
        else:
            c["n_btts_non"] += 1; c["ok_btts_non"] += int(bon_btts)

        # Double chance
        c["n_dc_12"] += 1; c["ok_dc_12"] += int(bon_dc_12)
        c["n_dc_1x"] += 1; c["ok_dc_1x"] += int(bon_dc_1x)

        resultats.append({
            "fixture_id": fx.fixture_id,
            "match": analyse["match"],
            "date": fx.date,
            "score": f"{score_home}-{score_away}",
            "pred_1x2": pred_1x2,   "reel_1x2": reel["1x2"],   "bon_1x2": bon_1x2,
            "pred_over25": pred_over25, "reel_over25": reel["over_2.5"], "bon_over25": bon_over25,
            "pred_over15": pred_over15, "reel_over15": reel_over15,      "bon_over15": bon_over15,
            "pred_btts": pred_btts,  "reel_btts": reel["btts"],  "bon_btts": bon_btts,
            "pred_dc_12": pred_dc_12, "bon_dc_12": bon_dc_12,
            "pred_dc_1x": pred_dc_1x, "bon_dc_1x": bon_dc_1x,
            "lam_dom": analyse["buts_attendus"]["domicile"],
            "lam_ext": analyse["buts_attendus"]["exterieur"],
        })

    def pct(n: int, d: int) -> float:
        return round(n / d * 100, 1) if d > 0 else 0.0

    total = c["total_1x2"]

    # Courbe de calibration : pour chaque bin de proba, taux de réussite réel
    calibration = []
    for i in range(10):
        b = cal_bins[i]
        if b["n"] > 0:
            calibration.append({
                "bin": f"{i*10}-{i*10+10}%",
                "proba_moyenne": round(b["somme_proba"] / b["n"] * 100, 1),
                "reussite_reelle": round(b["ok"] / b["n"] * 100, 1),
                "n": b["n"],
            })

    return {
        "league_id": league_id,
        "ligue": _nom_ligue(league_id),
        "saison": season,
        "total_matches": total,
        # 1X2 global
        "accuracy_1x2": pct(c["ok_1x2"], total),
        "ok_1x2": c["ok_1x2"],
        # Calibration (qualité scientifique des probabilités)
        "brier_score": round(somme_brier / total, 4) if total else None,
        "log_loss": round(somme_logloss / total, 4) if total else None,
        "calibration": calibration,
        # Over/Under 2.5 par direction
        "accuracy_over25":  pct(c["ok_over25"],  c["n_over25"]),
        "accuracy_under25": pct(c["ok_under25"], c["n_under25"]),
        "n_over25": c["n_over25"], "ok_over25": c["ok_over25"],
        "n_under25": c["n_under25"], "ok_under25": c["ok_under25"],
        # Over/Under 1.5 par direction
        "accuracy_over15":  pct(c["ok_over15"],  c["n_over15"]),
        "accuracy_under15": pct(c["ok_under15"], c["n_under15"]),
        "n_over15": c["n_over15"], "ok_over15": c["ok_over15"],
        "n_under15": c["n_under15"], "ok_under15": c["ok_under15"],
        # BTTS par direction
        "accuracy_btts_oui": pct(c["ok_btts_oui"], c["n_btts_oui"]),
        "accuracy_btts_non": pct(c["ok_btts_non"], c["n_btts_non"]),
        "n_btts_oui": c["n_btts_oui"], "ok_btts_oui": c["ok_btts_oui"],
        "n_btts_non": c["n_btts_non"], "ok_btts_non": c["ok_btts_non"],
        # Double chance
        "accuracy_dc_12": pct(c["ok_dc_12"], c["n_dc_12"]),
        "accuracy_dc_1x": pct(c["ok_dc_1x"], c["n_dc_1x"]),
        "ok_dc_12": c["ok_dc_12"], "n_dc_12": c["n_dc_12"],
        "ok_dc_1x": c["ok_dc_1x"], "n_dc_1x": c["n_dc_1x"],
        "matchs": resultats,
    }
