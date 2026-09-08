"""Modèles pré-match communs, entraînement chronologique et grille de scores.

Le modèle dynamique est une approximation à mises à jour de score, pas une
reproduction de l'estimation par espace d'état de Koopman/Lit.
"""
from collections import defaultdict, deque
from datetime import timedelta
from math import exp, log
import numpy as np
from scipy.optimize import minimize
from scipy.stats import poisson
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .calibration import ClassifieurCalibre, temperature_optimale, temperer
from .dixon_coles_fit import ajuster
from .elo import maj_elo, proba_1x2_elo
from .match_data import MODEL_VERSION, historique_90, utc
from .ml import _metriques
from .poisson import tau_dixon_coles
from .prediction_context import contexte_archive

CLES = ("1", "X", "2")
CONTEXT_FEATURES = ["elo_ecart", "repos_dom", "repos_ext", "matchs_7j_dom", "matchs_7j_ext",
                    "matchs_14j_dom", "matchs_14j_ext", "stabilite_dom", "stabilite_ext",
                    "absents_dom", "absents_ext"]
ML_FEATURES = CONTEXT_FEATURES + ["gf_dom", "gc_dom", "gf_ext", "gc_ext",
                                  "xgf_dom", "xga_dom", "xgf_ext", "xga_ext",
                                  "couverture_xg_dom", "couverture_xg_ext"]


def grille(lh, la, partage=0.0, rho=0.0):
    lh, la = np.clip([lh, la], 0.05, 8)
    partage = float(np.clip(partage, 0, min(lh, la) * 0.5))
    n = 25
    a = poisson.pmf(np.arange(n), lh - partage)
    b = poisson.pmf(np.arange(n), la - partage)
    g = np.zeros((n, n))
    for k, p in enumerate(poisson.pmf(np.arange(n), partage)):
        if p > 1e-12:
            g[k:, k:] += p * np.outer(a[:n-k], b[:n-k])
    if rho:
        for h in (0, 1):
            for v in (0, 1):
                g[h, v] *= max(0, tau_dixon_coles(h, v, lh, la, rho))
    return g / g.sum()


def p1x2(g):
    return np.array([np.tril(g, -1).sum(), np.trace(g), np.triu(g, 1).sum()])


def aligner_grille(g, probabilites):
    """Préserve les scores conditionnels ; impose le 1X2 du consensus partout."""
    h, a = np.indices(g.shape)
    out = g.copy()
    for mask, p in zip((h > a, h == a, h < a), probabilites):
        out[mask] *= p / max(out[mask].sum(), 1e-15)
    return out / out.sum()


def marches_grille(g):
    h, a = np.indices(g.shape)
    p = dict(zip(CLES, p1x2(g)))
    p.update({"1X": p["1"] + p["X"], "X2": p["X"] + p["2"], "12": p["1"] + p["2"]})
    for seuil in (1.5, 2.5):
        p[f"over_{seuil}"] = g[h + a > seuil].sum()
        p[f"under_{seuil}"] = 1 - p[f"over_{seuil}"]
    p["btts_oui"] = g[(h > 0) & (a > 0)].sum()
    p["btts_non"] = 1 - p["btts_oui"]
    return {k: round(float(v), 4) for k, v in p.items()}


class Etat:
    def __init__(self):
        self.elo = 1500.0
        self.attaque = self.defense = 0.0
        self.dates = deque(maxlen=60)
        self.forme = deque(maxlen=6)
        self.xg = deque(maxlen=6)  # Chaque match avance la fenêtre, même sans xG.


class Historique:
    def __init__(self):
        self.equipes = defaultdict(Etat)
        self.partage = 0.05

    def intensites(self, home, away, neutre=False):
        h, a = self.equipes[home], self.equipes[away]
        return (exp(log(1.35 if neutre else 1.5) + h.attaque - a.defense),
                exp(log(1.35 if neutre else 1.2) + a.attaque - h.defense))

    def update(self, f, xg):
        home, away = f["teams"]["home"]["id"], f["teams"]["away"]["id"]
        h, a = self.equipes[home], self.equipes[away]
        gh, ga = f["goals"]["home"], f["goals"]["away"]
        lh, la = self.intensites(home, away)
        # Régularisation des forces et adaptation progressive aux résidus.
        for equipe, attaque, defense in ((h, gh-lh, ga-la), (a, ga-la, gh-lh)):
            equipe.attaque = float(np.clip(0.995*equipe.attaque + 0.025*attaque, -1.1, 1.1))
            equipe.defense = float(np.clip(0.995*equipe.defense - 0.025*defense, -1.1, 1.1))
        self.partage = float(np.clip(0.98*self.partage + 0.02*(gh-lh)*(ga-la), 0, 0.35))
        h.elo, a.elo = maj_elo(h.elo, a.elo, gh, ga)
        date = utc(f["fixture"]["date"])
        for equipe, gf, gc in ((h, gh, ga), (a, ga, gh)):
            equipe.dates.append(date)
            equipe.forme.append((gf, gc))
        vals = xg.get(f["fixture"]["id"], {})
        xh, xa = vals.get(home), vals.get(away)
        valide = (f["fixture"]["status"]["short"] == "FT" and
                  all(isinstance(v, (int, float)) and np.isfinite(v) and v >= 0 for v in (xh, xa)))
        h.xg.append((date, xh, xa) if valide else None)
        a.xg.append((date, xa, xh) if valide else None)

    def features(self, home, away, date, contexte=None, neutre=False):
        h, a = self.equipes[home], self.equipes[away]
        date = utc(date)
        def repos(e):
            return min((date-e.dates[-1]).total_seconds()/86400, 30) if e.dates else np.nan
        def charge(e, n):
            return sum(0 < (date-d).total_seconds() <= n*86400 for d in e.dates)
        def moyenne(e, idx):
            return float(np.mean([v[idx] for v in e.forme])) if e.forme else np.nan
        def xgm(e):
            rows = [v for v in e.xg if v and 0 < (date-v[0]).days <= 90]
            return ([float(np.mean([v[1] for v in rows])), float(np.mean([v[2] for v in rows]))]
                    if rows else [np.nan, np.nan]), len(rows)/6
        ctx = contexte or {}
        try:
            if utc(ctx["observe_le"]) > date:
                ctx = {}
        except (KeyError, ValueError, TypeError):
            ctx = {}
        xh, ch = xgm(h)
        xa, ca = xgm(a)
        features = [h.elo-a.elo+(0 if neutre else 65), repos(h), repos(a), charge(h,7), charge(a,7),
                    charge(h,14), charge(a,14)] + [ctx.get(k, np.nan) for k in CONTEXT_FEATURES[7:]]
        features += [moyenne(h,0), moyenne(h,1), moyenne(a,0), moyenne(a,1), *xh, *xa, ch, ca]
        return np.asarray(features, dtype=float)


def replay(fixtures, xg):
    rows = historique_90(fixtures)
    state, pending, records = Historique(), deque(), []
    for f in rows:
        date = utc(f["fixture"]["date"])
        while pending and utc(pending[0]["fixture"]["date"]) + timedelta(hours=3) < date:
            state.update(pending.popleft(), xg)
        h, a = f["teams"]["home"]["id"], f["teams"]["away"]["id"]
        features = state.features(h, a, date, f.get("edge_context") or contexte_archive(f["fixture"]["id"], date))
        lh, la = state.intensites(h, a)
        gh, ga = f["goals"]["home"], f["goals"]["away"]
        records.append({"fixture": f, "x": features, "y": 0 if gh>ga else 1 if gh==ga else 2,
                        "elo": np.array(list(proba_1x2_elo(state.equipes[h].elo, state.equipes[a].elo).values())),
                        "dynamique": p1x2(grille(lh, la, state.partage)),
                        "xg_simple": simple_xg(features)})
        pending.append(f)
    return records


def simple_xg(x):
    if x[-2] < 0.5 or x[-1] < 0.5 or not np.isfinite(x[15:19]).all():
        return None
    # xG créés par une équipe et concédés par son adversaire.
    return p1x2(grille((x[15]+x[18])/2, (x[17]+x[16])/2))


def _classifieur(contexte=False):
    base = (LogisticRegression(C=0.25, max_iter=500) if contexte else
            HistGradientBoostingClassifier(max_iter=120, max_depth=3, l2_regularization=2, random_state=0))
    return make_pipeline(SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True),
                         StandardScaler(), base)


class Ensemble:
    def __init__(self):
        self.version = MODEL_VERSION
        self.contextuel = self.ml = self.dc = None
        self.weights = None
        self.sources_fit = []
        self.validation = {}
        self.trained_until = None
        self.temperature = 1.0

    def sources(self, state, home, away, date, contexte=None, neutre=False):
        x = state.features(home, away, date, contexte, neutre)
        h, a = state.equipes[home], state.equipes[away]
        lh, la = state.intensites(home, away, neutre)
        gd = grille(lh, la, state.partage)
        gp = gd
        if self.dc and self.dc.connait(home) and self.dc.connait(away):
            ph, pa = self.dc.buts_attendus(home, away, terrain_neutre=neutre)
            gp = grille(ph, pa, rho=self.dc.rho)
        sources = {"poisson": p1x2(gp), "elo": np.array(list(proba_1x2_elo(h.elo,a.elo,terrain_neutre=neutre).values())),
                   "dynamique": p1x2(gd)}
        for name, model, xx in (("contextuel", self.contextuel, x[:len(CONTEXT_FEATURES)]), ("ml", self.ml, x)):
            if model:
                sources[name] = model.predict_proba([xx])[0]
        pxg = simple_xg(x)
        if pxg is not None:
            sources["xg_simple"] = pxg
        return sources, gp, {"domicile": "".join("W" if gf>gc else "D" if gf==gc else "L" for gf,gc in h.forme),
                             "exterieur": "".join("W" if gf>gc else "D" if gf==gc else "L" for gf,gc in a.forme)}


def entrainer_ensemble(fixtures, xg):
    records = replay(fixtures, xg)
    model = Ensemble()
    if len(records) < 180:
        return None
    x = np.array([r["x"] for r in records])
    y = np.array([r["y"] for r in records])
    # Quatre blocs : entraînement, calibration, fusion, test final intact.
    cuts = []
    for frac in (0.5, 0.65, 0.8):
        cut = int(len(records)*frac)
        while cut > 0 and records[cut-1]["fixture"]["fixture"]["date"] >= records[cut]["fixture"]["fixture"]["date"]:
            cut -= 1
        cuts.append(cut)
    t, c, v = cuts
    if min(t,c-t,v-c,len(y)-v) < 20 or len(set(y[:t])) < 3:
        return None
    model.trained_until = records[-1]["fixture"]["fixture"]["date"]
    cutoff = utc(records[t]["fixture"]["fixture"]["date"])
    def avant_frontiere(start, end):
        limite = utc(records[end]["fixture"]["fixture"]["date"]) - timedelta(hours=3)
        while end > start and utc(records[end-1]["fixture"]["fixture"]["date"]) >= limite:
            end -= 1
        return end
    tf, cf, vf = avant_frontiere(0,t), avant_frontiere(t,c), avant_frontiere(c,v)
    if min(tf,cf-t,vf-c) < 20 or len(set(y[:tf])) < 3:
        return None
    model.dc = ajuster([r["fixture"] for r in records[:t]], ref_date=cutoff)
    for name, xx in (("contextuel", x[:,:len(CONTEXT_FEATURES)]), ("ml", x)):
        base = _classifieur(name == "contextuel")
        base.fit(xx[:tf], y[:tf])
        calibrated = ClassifieurCalibre(base, temperature_optimale(base.predict_proba(xx[t:cf]), y[t:cf]))
        setattr(model, name, calibrated)
    names = ["poisson", "elo", "dynamique", "contextuel", "ml"]
    predicted = {"elo": np.array([r["elo"] for r in records]), "dynamique": np.array([r["dynamique"] for r in records])}
    predicted["contextuel"] = model.contextuel.predict_proba(x[:,:len(CONTEXT_FEATURES)])
    predicted["ml"] = model.ml.predict_proba(x)
    pp = []
    for r in records:
        f = r["fixture"]
        h,a = f["teams"]["home"]["id"], f["teams"]["away"]["id"]
        if model.dc and model.dc.connait(h) and model.dc.connait(a):
            lh, la = model.dc.buts_attendus(h, a)
            pp.append(p1x2(grille(lh, la, rho=model.dc.rho)))
        else:
            pp.append(r["dynamique"])
    predicted["poisson"] = np.array(pp)
    # Le xG simple n'entre dans la fusion que si la couverture du bloc est complète.
    if all(r["xg_simple"] is not None for r in records[c:]):
        names.append("xg_simple")
        predicted["xg_simple"] = np.array([r["xg_simple"] if r["xg_simple"] is not None else r["elo"] for r in records])
    logs = np.log(np.clip(np.stack([predicted[n] for n in names], axis=1),1e-9,1))
    baseline_w = np.array([0.3,0.7]+[0.]*(len(names)-2))
    def pooled(weights, sl):
        z = np.sum(logs[sl]*weights[None,:,None], axis=1)
        return temperer(np.exp(z))
    def objective(w):
        p = pooled(w,slice(c,vf))
        return -np.log(p[np.arange(vf-c),y[c:vf]]).mean()+0.015*np.square(w-baseline_w).sum()
    fit = minimize(objective, baseline_w, bounds=[(0,1)]*len(names),
                   constraints=[{"type":"eq","fun":lambda w:w.sum()-1}], method="SLSQP")
    w = fit.x if fit.success else baseline_w
    p_test, p_base = pooled(w,slice(v,None)), pooled(baseline_w,slice(v,None))
    metrics = {n:_metriques(p[v:],y[v:]) for n,p in predicted.items()}
    metrics["fusion_candidate"] = _metriques(p_test,y[v:])
    metrics["baseline"] = _metriques(p_base,y[v:])
    mid = len(p_test)//2
    fenetres = []
    for start,end in ((0,mid),(mid,len(p_test))):
        labels = y[v+start:v+end]
        idx = np.arange(end-start)
        candidate = float(-np.log(p_test[start:end][idx,labels]).mean())
        reference = float(-np.log(p_base[start:end][idx,labels]).mean())
        fenetres.append({"n":end-start,"log_loss_candidate":candidate,"log_loss_reference":reference})
    accepted = all(f["log_loss_candidate"] < f["log_loss_reference"] for f in fenetres)
    model.weights = dict(zip(names, map(float, w if accepted else baseline_w)))
    model.sources_fit = names
    model.validation = {"n_train":tf,"n_calibration":cf-t,"n_fusion":vf-c,"n_test":len(y)-v,
                        "fenetres_test":fenetres,"n_exclus_frontieres":(t-tf)+(c-cf)+(v-vf),
                        "debut_test":records[v]["fixture"]["fixture"]["date"],
                        "fin_test":model.trained_until,"fusion_retenue":accepted,"metriques":metrics,
                        "note":"Test chronologique final ; sélection de déploiement sur ce bloc, à confirmer prospectivement."}
    return model
