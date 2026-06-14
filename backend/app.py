"""Petit serveur web : page HTML + bouton qui génère le ticket.

Lancer :
    python app.py
Puis ouvrir http://127.0.0.1:8000

L'endpoint /api/generer fait tourner le pipeline et renvoie le JSON
(combinés + analyses). Grâce au cache disque, recliquer ne reconsomme
pas le quota API.
"""
import logging
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ===================== Logging =====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("edge")

from src import store
from src.analyste import analyser_avec_ia
from src.api_client import ApiFootball
from src.blend import conseil_consensus
from src.consensus import consensus_match
from src.ligues_mise_o_jeu import IDS_SOCCER, LIGUES_SOCCER
from src.odds_parser import recuperer_cotes
from src.pipeline import (
    STATUTS_LIVE,
    STATUTS_TERMINES,
    STATUTS_UPCOMING,
    _nom_ligue,
    analyser_fixture,
    analyser_fixture_sans_cotes,
    conseil_de_paris,
    fixtures_depuis_reponse,
)
from src.tickets import (
    construire_selection,
    generer_tickets_confiance,
    selection_confiance,
)


# ===================== Grading automatique =====================

def _grader_selection(cle: str, score_home: int, score_away: int) -> bool | None:
    """Grade une sélection selon la clé marché et le score final."""
    total = score_home + score_away
    if cle == "1":         return score_home > score_away
    if cle == "X":         return score_home == score_away
    if cle == "2":         return score_away > score_home
    if cle == "1X":        return score_home >= score_away
    if cle == "12":        return score_home != score_away
    if cle == "X2":        return score_away >= score_home
    if cle == "btts_oui":  return score_home > 0 and score_away > 0
    if cle == "btts_non":  return score_home == 0 or score_away == 0
    # Over/Under générique : "over_2.5", "under_1.5", etc.
    if cle.startswith("over_"):
        try:
            seuil = float(cle[5:])
            return total > seuil
        except ValueError:
            pass
    if cle.startswith("under_"):
        try:
            seuil = float(cle[6:])
            return total < seuil
        except ValueError:
            pass
    return None


def _match_terminé(match_date: str) -> bool:
    """Vrai si le match a démarré il y a plus de 2h (le temps qu'il soit fini)."""
    if not match_date:
        return True  # date inconnue → on tente quand même
    try:
        dt = datetime.fromisoformat(match_date)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) >= dt + timedelta(hours=2)
    except ValueError:
        return True


def _settle_tickets() -> dict:
    """Vérifie les résultats API-Football pour les tickets en_attente dont les matchs sont terminés.

    N'appelle l'API que pour les fixtures dont l'heure de coup d'envoi + 2h est passée,
    afin de ne pas gaspiller le quota API-Football.
    """
    tickets = store.lister_tickets()
    en_attente = [t for t in tickets if t["statut"] == "en_attente"]
    if not en_attente:
        return {"settled": 0, "skipped": 0}

    # Collecte les fixture_id à vérifier (matchs potentiellement terminés seulement)
    fids_a_checker: set[int] = set()
    for ticket in en_attente:
        for sel in ticket["selections"]:
            fid = sel.get("fixture_id", 0)
            if fid and sel.get("cle") and _match_terminé(sel.get("match_date", "")):
                fids_a_checker.add(fid)

    if not fids_a_checker:
        return {"settled": 0, "skipped": len(en_attente)}

    api = ApiFootball()
    cache_scores: dict[int, dict | None] = {}

    for fid in fids_a_checker:
        try:
            # Toujours frais : on a besoin du score final réel, pas du cache
            data = api.get("fixtures", {"id": fid}, use_cache=False)
            resp = data.get("response", [])
            if not resp:
                cache_scores[fid] = None
                continue
            f = resp[0]
            if f["fixture"]["status"]["short"] not in ("FT", "AET", "PEN"):
                cache_scores[fid] = None
                continue
            s = f["score"]["fulltime"]
            cache_scores[fid] = {"home": s["home"], "away": s["away"]}
        except Exception:
            cache_scores[fid] = None

    settled = 0
    for ticket in en_attente:
        resultats = []
        for sel in ticket["selections"]:
            fid = sel.get("fixture_id", 0)
            cle = sel.get("cle", "")
            if not fid or not cle:
                resultats.append(None)
                continue
            score = cache_scores.get(fid)
            if score is None:
                resultats.append(None)
                continue
            resultats.append(_grader_selection(cle, score["home"], score["away"]))

        if any(r is False for r in resultats):
            store.definir_statut(ticket["id"], "perdu")
            settled += 1
        elif resultats and all(r is True for r in resultats):
            store.definir_statut(ticket["id"], "gagne")
            settled += 1

    return {"settled": settled, "skipped": len(en_attente) - settled}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    store.init_db()
    log.info("EDGE API démarrée — base initialisée")
    try:
        _settle_tickets()
    except Exception as e:
        log.exception("settlement au démarrage: ÉCHEC : %s", e)
    yield


app = FastAPI(title="BET — API", lifespan=lifespan)

# Autorise le frontend Next.js (dev) à appeler l'API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", "http://127.0.0.1:3000",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def racine():
    return {"service": "BET API", "ok": True}


@app.get("/api/ligues")
def ligues():
    """Liste blanche des ligues offertes par Mise-o-jeu (validateur)."""
    return [{"id": lid, "nom": nom} for lid, nom in LIGUES_SOCCER.items()]


def _fenetre_dates(jours_avant: int = 7, jours_passe: int = 0) -> list[str]:
    """Dates à scanner : des `jours_passe` jours passés à `jours_avant` à venir."""
    today = date.today()
    return [(today + timedelta(days=i)).isoformat()
            for i in range(-jours_passe, jours_avant + 1)]


def _scanner_fixtures(api, jours: int, valider: int, max_matchs: int,
                       statuts_autorises=None, jours_passe: int = 0):
    """Récupère les matchs sur la fenêtre de dates. -> (fixtures, dates_ok)."""
    autorisees = IDS_SOCCER if valider else None
    if statuts_autorises is None:
        statuts_autorises = STATUTS_UPCOMING
    fixtures, dates_ok = [], []
    for d in _fenetre_dates(jours, jours_passe):
        try:
            data = api.get("fixtures", {"date": d})
        except Exception:
            continue
        dates_ok.append(d)
        fixtures += fixtures_depuis_reponse(
            data.get("response", []),
            ligues_autorisees=autorisees,
            statuts_autorises=statuts_autorises,
        )
    return fixtures[:max_matchs], dates_ok


@app.get("/api/generer")
def generer(
    nb_tickets: int = 3,
    cote_cible: float = 3.0,
    stats_season: int | None = None,  # None = saison réelle de chaque match (PRO)
    max_matchs: int = 30,
    valider: int = 1,           # 1 = liste blanche Mise-o-jeu ; 0 = tous
    jours: int = 7,             # nombre de jours à venir à scanner
):
    """Scan AUTOMATIQUE : tickets sur les issues les PLUS PROBABLES (consensus).

    Nouvelle philosophie : on ne chasse plus une cote cible. Pour chaque match
    on calcule le consensus multi-modèles (Poisson ajusté + Elo + marché) et on
    ne retient que les issues à forte confiance. Les tickets regroupent les
    paris les plus sûrs (le ticket #1 = les plus solides).
    """
    try:
        api = ApiFootball()
        fixtures, dates_ok = _scanner_fixtures(api, jours, valider, max_matchs)

        selections = []
        analyses = []
        for fx in fixtures:
            try:
                cotes = recuperer_cotes(api, fx.fixture_id)
            except Exception as e:
                log.exception("generer: cotes ÉCHEC fixture=%s : %s", fx.fixture_id, e)
                cotes = {}
            cotes_1x2 = {k: cotes.get(k) for k in ("1", "X", "2") if cotes.get(k)}

            mm = consensus_match(api, fx.league, fx.season, fx.home_id, fx.away_id,
                                 cotes_1x2=cotes_1x2 or None)
            cons = mm["consensus"].get("probabilites")
            if not cons:
                continue

            match_label = f"{fx.home_name} - {fx.away_name}"
            pick = selection_confiance(cons, cotes)
            analyses.append({
                "match": match_label,
                "ligue": _nom_ligue(fx.league),
                "fixture_id": fx.fixture_id,
                "date": fx.date,
                "consensus": cons,
                "pick": ({"cle": pick[0], "proba": round(pick[1], 4)} if pick else None),
            })

            if pick:
                cle, proba = pick
                sel = construire_selection(match_label, _nom_ligue(fx.league),
                                           fx.fixture_id, fx.date, cle, proba, cotes)
                if sel.cote > 0:  # besoin d'une cote pour afficher/grader
                    selections.append(sel)

        log.info("generer: %s matchs, %s sélections à forte confiance",
                 len(analyses), len(selections))

        combines = generer_tickets_confiance(selections, nb_tickets=nb_tickets)
        combines_json = [{
            "cote_totale": round(c.cote_totale, 2),
            "proba_reussite": round(c.proba_combinee, 4),
            "value": round(c.value_combinee, 4),
            "selections": [
                {"match": s.match, "ligue": s.ligue, "marche": s.marche,
                 "cote": s.cote, "proba": round(s.proba, 4),
                 "fixture_id": s.fixture_id, "cle": s.cle, "match_date": s.match_date}
                for s in c.selections
            ],
        } for c in combines]

        return JSONResponse({
            "genere_le": datetime.now(timezone.utc).isoformat(),
            "nb_matchs_analyses": len(analyses),
            "nb_combines": len(combines_json),
            "combines": combines_json,
            "analyses": analyses,
            "dates_scannees": dates_ok,
            "validateur_mise_o_jeu": bool(valider),
        })
    except Exception as e:
        log.exception("generer: ÉCHEC : %s", e)
        return JSONResponse({"erreur": str(e)}, status_code=500)


@app.get("/api/analyses")
def analyses(
    stats_season: int | None = None,
    max_matchs: int = 40,
    valider: int = 1,
    jours: int = 7,
    jours_passe: int = 2,
):
    """Liste des matchs analysés (probas + forme), pour la page Analyses.

    jours_passe : nombre de jours passés à inclure (matchs récemment terminés
    restent visibles, marqués Terminé + score).
    """
    try:
        api = ApiFootball()
        fixtures, dates_ok = _scanner_fixtures(
            api, jours, valider, max_matchs,
            statuts_autorises=STATUTS_UPCOMING | STATUTS_LIVE | STATUTS_TERMINES,
            jours_passe=jours_passe,
        )
        log.info("analyses: %s matchs trouvés sur %s dates (passé=%s, avant=%s)",
                 len(fixtures), len(dates_ok), jours_passe, jours)
        out = []
        ignores = 0
        for fx in fixtures:
            r = analyser_fixture_sans_cotes(api, fx, stats_season=stats_season)
            if r:
                out.append(r)
            else:
                ignores += 1
        log.info("analyses: %s analysés, %s ignorés (données insuffisantes)", len(out), ignores)
        return JSONResponse({"dates_scannees": dates_ok, "nb": len(out), "analyses": out})
    except Exception as e:
        log.exception("analyses: ÉCHEC : %s", e)
        return JSONResponse({"erreur": str(e)}, status_code=500)


def _classement(api, league: int, season: int, home_id: int, away_id: int,
                frais: bool = False) -> dict | None:
    """Classement COMPLET du championnat — bypass cache si le match est live/récent."""
    try:
        data = api.get("standings", {"league": league, "season": season}, use_cache=not frais)
    except Exception as e:
        log.exception("classement: ÉCHEC league=%s season=%s : %s", league, season, e)
        return None
    resp = data.get("response", [])
    if not resp:
        return None
    groupes = []
    for groupe in resp[0].get("league", {}).get("standings", []):
        lignes, nom = [], None
        for e in groupe:
            nom = e.get("group") or nom
            lignes.append({
                "rang": e.get("rank"),
                "equipe_id": e.get("team", {}).get("id"),
                "equipe": e.get("team", {}).get("name"),
                "logo": e.get("team", {}).get("logo"),
                "points": e.get("points"),
                "joues": e.get("all", {}).get("played"),
                "diff": e.get("goalsDiff"),
                "forme": e.get("form"),
            })
        if lignes:
            groupes.append({"nom": nom or "Classement", "lignes": lignes})
    if not groupes:
        return None
    return {"groupes": groupes, "home_id": home_id, "away_id": away_id}


def _derniers_matchs(api, team_id: int) -> list[dict]:
    """5 derniers matchs d'une équipe avec score réel."""
    try:
        data = api.get("fixtures", {"team": team_id, "last": 5})
        out = []
        for f in data.get("response", []):
            sh = f["score"]["fulltime"]["home"]
            sa = f["score"]["fulltime"]["away"]
            if sh is None or sa is None:
                continue
            est_dom = f["teams"]["home"]["id"] == team_id
            resultat = (
                "W" if (est_dom and sh > sa) or (not est_dom and sa > sh)
                else "D" if sh == sa else "L"
            )
            out.append({
                "date": f["fixture"]["date"],
                "domicile": f["teams"]["home"]["name"],
                "exterieur": f["teams"]["away"]["name"],
                "score": f"{sh}-{sa}",
                "resultat": resultat,
                "a_domicile": est_dom,
            })
        return out
    except Exception as e:
        log.exception("derniers_matchs: ÉCHEC team=%s : %s", team_id, e)
        return []


def _h2h(api, home_id: int, away_id: int) -> list[dict]:
    """5 dernières confrontations directes."""
    try:
        data = api.get("fixtures/headtohead", {"h2h": f"{home_id}-{away_id}", "last": 5})
        out = []
        for f in data.get("response", []):
            sh = f["score"]["fulltime"]["home"]
            sa = f["score"]["fulltime"]["away"]
            if sh is None or sa is None:
                continue
            out.append({
                "date": f["fixture"]["date"],
                "domicile": f["teams"]["home"]["name"],
                "exterieur": f["teams"]["away"]["name"],
                "score": f"{sh}-{sa}",
                "home_id": f["teams"]["home"]["id"],
            })
        return out
    except Exception as e:
        log.exception("h2h: ÉCHEC %s-%s : %s", home_id, away_id, e)
        return []


def _compos(api, fixture_id: int, status: str = "") -> list[dict]:
    """Compositions — bypass cache si le match est live ou à venir (lineup peut changer)."""
    try:
        # Pour les matchs actifs ou récents, on force un fetch frais
        frais = status in STATUTS_LIVE or status in STATUTS_UPCOMING or status == ""
        log.info("compos: fixture=%s status=%s (fetch %s)", fixture_id, status,
                 "FRAIS" if frais else "cache")
        data = api.get("fixtures/lineups", {"fixture": fixture_id}, use_cache=not frais)
        n = len(data.get("response", []))

        # Auto-réparation : si le cache renvoie une compo vide (mise en cache
        # avant publication des lineups), on retente une fois sans cache.
        if n == 0 and not frais:
            log.warning("compos: fixture=%s vide en cache -> retry sans cache", fixture_id)
            data = api.get("fixtures/lineups", {"fixture": fixture_id}, use_cache=False)
            n = len(data.get("response", []))

        log.info("compos: fixture=%s -> %s équipe(s)", fixture_id, n)
        if n == 0:
            log.warning("compos: fixture=%s AUCUNE compo (API n'a pas encore les lineups)", fixture_id)

        out = []
        for t in data.get("response", []):
            out.append({
                "equipe": t["team"]["name"],
                "logo": t["team"].get("logo"),
                "formation": t.get("formation"),
                "titulaires": [
                    {"id": p["player"].get("id"),
                     "numero": p["player"].get("number"),
                     "nom": p["player"]["name"],
                     "poste": p["player"].get("pos"),
                     "grid": p["player"].get("grid")}
                    for p in t.get("startXI", [])
                ],
                "remplacants": [
                    {"id": p["player"].get("id"),
                     "numero": p["player"].get("number"),
                     "nom": p["player"]["name"],
                     "poste": p["player"].get("pos")}
                    for p in t.get("substitutes", [])
                ],
            })
        return out
    except Exception as e:
        log.exception("compos: ÉCHEC fixture=%s : %s", fixture_id, e)
        return []


def _detail_match(api, fixture_id: int, stats_season: int | None = None) -> dict:
    """Construit le détail complet d'un match (probas, value, conseil, équipes)."""
    log.info("detail_match: fixture=%s ====================", fixture_id)
    # Sans cache : le statut/score d'un match évolue (NS -> live -> FT). Un
    # fixture mis en cache à l'état "à venir" donnerait un score périmé.
    data = api.get("fixtures", {"id": fixture_id}, use_cache=False)
    resp = data.get("response", [])
    if not resp:
        log.warning("detail_match: fixture=%s INTROUVABLE", fixture_id)
        raise HTTPException(status_code=404, detail="Match introuvable")
    f = resp[0]
    fx = fixtures_depuis_reponse([f])[0]
    log.info("detail_match: %s vs %s | status=%s | score=%s-%s",
             fx.home_name, fx.away_name, fx.status, fx.buts_dom, fx.buts_ext)

    res = analyser_fixture(api, fx, stats_season=stats_season)
    if res:
        res["conseil"] = conseil_de_paris(res.get("selections", []))
    else:
        res = analyser_fixture_sans_cotes(api, fx, stats_season=stats_season)
        if not res:
            raise HTTPException(status_code=422, detail="Données insuffisantes pour ce match")
        res["selections"] = []
        res["conseil"] = conseil_de_paris(
            [{"marche": m["marche"], "proba": m["proba"], "value": 0}
             for m in res.get("marches", [])]
        )

    res["date"] = f["fixture"]["date"]
    res["league_id"] = f["league"]["id"]
    res["round"] = f["league"].get("round", "")
    res["home"] = {
        "id": f["teams"]["home"]["id"],
        "name": f["teams"]["home"]["name"],
        "logo": f["teams"]["home"].get("logo"),
    }
    res["away"] = {
        "id": f["teams"]["away"]["id"],
        "name": f["teams"]["away"]["name"],
        "logo": f["teams"]["away"].get("logo"),
    }
    match_status = f["fixture"]["status"]["short"]
    est_frais = match_status in STATUTS_LIVE or match_status in {"FT", "AET", "PEN"}
    res["classement"] = _classement(api, fx.league, fx.season, fx.home_id, fx.away_id, frais=est_frais)
    res["derniers_matchs_dom"] = _derniers_matchs(api, fx.home_id)
    res["derniers_matchs_ext"] = _derniers_matchs(api, fx.away_id)
    res["h2h"] = _h2h(api, fx.home_id, fx.away_id)
    res["compos"] = _compos(api, fixture_id, status=f["fixture"]["status"]["short"])
    res["multi_modeles"] = _multi_modeles(api, fx, res)
    return res


# Nations hôtes du Mondial 2026 (terrain réel, pas neutre)
HOTES_WC_2026 = {2, 16, 101}  # USA, Mexico, Canada
LIGUES_NATIONALES = {1, 4, 5, 9, 10, 29, 30, 31, 32, 33, 34}


def _multi_modeles(api, fx, res: dict) -> dict:
    """Calcule Elo + marché + consensus pondéré pour le 1X2.

    Combine trois estimations indépendantes (Poisson/DC, Elo, marché) en un
    consensus statistique. Tolérant aux erreurs : toute source qui échoue est
    simplement omise.
    """
    # Poisson par moyennes brutes (déjà dans res) servant de repli si le modèle
    # Dixon-Coles ajusté n'est pas disponible pour ce match.
    probas = res.get("probabilites", {})
    poisson_fallback = ({k: probas.get(k) for k in ("1", "X", "2")}
                        if probas.get("1") is not None else None)
    cotes_1x2 = {s.get("cle"): s.get("cote") for s in res.get("selections", [])
                 if s.get("cle") in ("1", "X", "2") and s.get("cote")}

    mm = consensus_match(api, fx.league, fx.season, fx.home_id, fx.away_id,
                         cotes_1x2=cotes_1x2 or None, poisson_fallback=poisson_fallback)

    # Le conseil est fondé sur le CONSENSUS (cohérent avec la carte affichée),
    # pas sur le Poisson seul. La value se mesure contre le marché.
    probas_cons = mm["consensus"].get("probabilites")
    if probas_cons:
        cotes_all = {s.get("cle"): s.get("cote") for s in res.get("selections", [])
                     if s.get("cote")}
        conseil = conseil_consensus(probas_cons, cotes_all)
        if conseil:
            res["conseil"] = conseil

    return mm


@app.get("/api/match/{fixture_id}")
def match_detail(fixture_id: int, stats_season: int | None = None):
    """Analyse approfondie d'un match + conseil de paris (statistique)."""
    try:
        api = ApiFootball()
        return JSONResponse(_detail_match(api, fixture_id, stats_season))
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"erreur": str(e)}, status_code=500)


@app.get("/api/match/{fixture_id}/ia")
def match_ia(fixture_id: int, stats_season: int | None = None,
             force: int = 0, cache_only: int = 0):
    """Analyse fine par le cerveau LLM (DeepSeek) — à la demande, avec cache.

    force=1      force une nouvelle analyse (ignore le cache).
    cache_only=1 ne renvoie QUE le cache à jour (jamais d'appel DeepSeek) ;
                 répond {"cache_absent": true} si rien d'exploitable. Sert à
                 l'affichage auto à l'ouverture du match, sans coût.
    """
    try:
        if not force:
            cache = store.get_analyse_ia(fixture_id)
            # On ne sert le cache que s'il est au FORMAT À JOUR (verdict d'équipe).
            # Les analyses à l'ancien format sont régénérées automatiquement.
            if cache and "probabilites_finales" in cache:
                log.info("ia: fixture=%s servie depuis le cache", fixture_id)
                return JSONResponse(cache)
            if cache_only:
                # Pas de cache exploitable et on interdit l'appel DeepSeek.
                return JSONResponse({"cache_absent": True})
            if cache:
                log.info("ia: fixture=%s cache obsolète (ancien format) -> régénération", fixture_id)

        if cache_only:
            return JSONResponse({"cache_absent": True})

        log.info("ia: fixture=%s analyse DeepSeek (force=%s)…", fixture_id, force)
        api = ApiFootball()
        detail = _detail_match(api, fixture_id, stats_season)
        res = analyser_avec_ia(api, detail)
        store.save_analyse_ia(fixture_id, res)
        res["cache"] = False
        log.info("ia: fixture=%s OK (prediction=%s)", fixture_id, res.get("prediction"))
        return JSONResponse(res)
    except HTTPException:
        raise
    except Exception as e:
        log.exception("ia: ÉCHEC fixture=%s : %s", fixture_id, e)
        return JSONResponse({"erreur": str(e)}, status_code=500)


# ===================== Tickets sauvegardés (history) =====================

class SelectionIn(BaseModel):
    match: str
    ligue: str = ""
    marche: str
    cote: float
    proba: float
    fixture_id: int = 0
    cle: str = ""


class TicketIn(BaseModel):
    cote_totale: float
    proba_reussite: float
    value: float = 0.0
    mise: float = 10.0
    selections: list[SelectionIn]


class StatutIn(BaseModel):
    statut: str  # en_attente | gagne | perdu


@app.post("/api/tickets")
def creer_ticket(body: TicketIn):
    combine = {
        "cote_totale": body.cote_totale,
        "proba_reussite": body.proba_reussite,
        "value": body.value,
        "selections": [s.model_dump() for s in body.selections],
    }
    return store.sauver_ticket(combine, mise=body.mise)


@app.get("/api/tickets")
def get_tickets():
    return store.lister_tickets()


@app.patch("/api/tickets/{ticket_id}")
def maj_ticket(ticket_id: int, body: StatutIn):
    try:
        t = store.definir_statut(ticket_id, body.statut)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not t:
        raise HTTPException(status_code=404, detail="Ticket introuvable")
    return t


@app.delete("/api/tickets/{ticket_id}")
def del_ticket(ticket_id: int):
    store.supprimer_ticket(ticket_id)
    return {"ok": True}


@app.post("/api/tickets/settle")
def settle():
    """Vérifie les résultats API-Football et grade automatiquement les tickets en_attente."""
    try:
        return _settle_tickets()
    except Exception as e:
        return JSONResponse({"erreur": str(e)}, status_code=500)


@app.get("/api/analytics")
def get_analytics():
    return store.analytics()


@app.get("/api/backtest")
def backtest(league: int, season: int, limit: int = 0):
    from src.backtest import run_backtest
    api = ApiFootball()
    result = run_backtest(api, league, season, limit=limit or None)
    return JSONResponse(result)


# ===================== Équipes & Joueurs =====================

@app.get("/api/team/{team_id}")
def team_detail(team_id: int):
    """Profil complet d'une équipe : infos, forme, 15 derniers matchs, stats."""
    try:
        api = ApiFootball()
        team_data = api.get("teams", {"id": team_id})
        team_resp = team_data.get("response", [])
        if not team_resp:
            raise HTTPException(status_code=404, detail="Équipe introuvable")

        team  = team_resp[0]["team"]
        venue = team_resp[0].get("venue", {})

        fix_data = api.get("fixtures", {"team": team_id, "last": 15})
        matchs = []
        for f in fix_data.get("response", []):
            sh = f["score"]["fulltime"]["home"]
            sa = f["score"]["fulltime"]["away"]
            if sh is None or sa is None:
                continue
            est_dom = f["teams"]["home"]["id"] == team_id
            res = ("W" if (est_dom and sh > sa) or (not est_dom and sa > sh)
                   else "D" if sh == sa else "L")
            matchs.append({
                "fixture_id": f["fixture"]["id"],
                "date": f["fixture"]["date"],
                "ligue": f["league"]["name"],
                "ligue_logo": f["league"].get("logo"),
                "adversaire_id": f["teams"]["away"]["id"] if est_dom else f["teams"]["home"]["id"],
                "adversaire": f["teams"]["away"]["name"] if est_dom else f["teams"]["home"]["name"],
                "adversaire_logo": f["teams"]["away"].get("logo") if est_dom else f["teams"]["home"].get("logo"),
                "a_domicile": est_dom,
                "score": f"{sh}-{sa}",
                "resultat": res,
                "buts_pour": sh if est_dom else sa,
                "buts_contre": sa if est_dom else sh,
            })

        nb = len(matchs)
        wins   = sum(1 for m in matchs if m["resultat"] == "W")
        draws  = sum(1 for m in matchs if m["resultat"] == "D")
        losses = sum(1 for m in matchs if m["resultat"] == "L")
        bp = sum(m["buts_pour"] for m in matchs)
        bc = sum(m["buts_contre"] for m in matchs)

        return JSONResponse({
            "id": team["id"],
            "nom": team["name"],
            "logo": team.get("logo"),
            "pays": team.get("country"),
            "stade": venue.get("name"),
            "ville": venue.get("city"),
            "stats": {
                "matchs": nb,
                "victoires": wins,
                "nuls": draws,
                "defaites": losses,
                "buts_pour": bp,
                "buts_contre": bc,
                "moy_bp": round(bp / nb, 2) if nb else 0,
                "moy_bc": round(bc / nb, 2) if nb else 0,
            },
            "forme": "".join(m["resultat"] for m in matchs[-5:]),
            "matchs": matchs,
        })
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"erreur": str(e)}, status_code=500)


@app.get("/api/player/{player_id}")
def player_detail(player_id: int):
    """Profil d'un joueur : infos + stats de la saison en cours."""
    try:
        from datetime import date as dt_date
        api  = ApiFootball()
        season = dt_date.today().year if dt_date.today().month >= 7 else dt_date.today().year - 1
        data = api.get("players", {"id": player_id, "season": season})
        resp = data.get("response", [])
        if not resp:
            raise HTTPException(status_code=404, detail="Joueur introuvable")

        p          = resp[0]["player"]
        all_stats  = resp[0].get("statistics", [{}])

        # Équipe principale = compétition avec le plus de minutes jouées
        main = max(all_stats, key=lambda s: s.get("games", {}).get("minutes") or 0)
        team = main.get("team", {})

        def _sum(key1: str, key2: str) -> int:
            return sum((s.get(key1, {}).get(key2) or 0) for s in all_stats)

        def _avg_rating() -> str | None:
            pairs = [(float(s["games"]["rating"]), s["games"].get("appearences") or 1)
                     for s in all_stats if s.get("games", {}).get("rating")]
            if not pairs: return None
            num = sum(r * w for r, w in pairs)
            den = sum(w for _, w in pairs)
            return f"{num / den:.1f}" if den else None

        return JSONResponse({
            "id": p["id"],
            "nom": p["name"],
            "prenom": p.get("firstname"),
            "nom_famille": p.get("lastname"),
            "photo": p.get("photo"),
            "nationalite": p.get("nationality"),
            "naissance": p.get("birth", {}).get("date"),
            "taille": p.get("height"),
            "poids": p.get("weight"),
            "poste": main.get("games", {}).get("position"),
            "equipe_id": team.get("id"),
            "equipe": team.get("name"),
            "equipe_logo": team.get("logo"),
            "saison": season,
            "stats": {
                "matchs": _sum("games", "appearences"),
                "titularisations": _sum("games", "lineups"),
                "minutes": _sum("games", "minutes"),
                "buts": _sum("goals", "total"),
                "passes_decisives": _sum("goals", "assists"),
                "cartons_jaunes": _sum("cards", "yellow"),
                "cartons_rouges": _sum("cards", "red"),
                "passes": _sum("passes", "total"),
                "note": _avg_rating(),
            },
        })
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"erreur": str(e)}, status_code=500)


# ===================== Scores (navigation par date) =====================

@app.get("/api/scores")
def scores_du_jour(date_str: str = ""):
    """Tous les matchs d'une date dans nos ligues — passés, live, à venir."""
    try:
        from datetime import date as dt_date
        target = date_str or dt_date.today().isoformat()
        api = ApiFootball()
        data = api.get("fixtures", {"date": target})
        resp = data.get("response", [])
        ids_autorises = set(IDS_SOCCER)
        out = []
        for f in resp:
            if f["league"]["id"] not in ids_autorises:
                continue
            status = f["fixture"]["status"]["short"]
            goals = f["goals"]
            out.append({
                "fixture_id": f["fixture"]["id"],
                "status": status,
                "elapsed": f["fixture"]["status"].get("elapsed"),
                "heure": f["fixture"]["date"],
                "ligue_id": f["league"]["id"],
                "ligue": f["league"]["name"],
                "ligue_logo": f["league"].get("logo"),
                "home": {
                    "id": f["teams"]["home"]["id"],
                    "name": f["teams"]["home"]["name"],
                    "logo": f["teams"]["home"].get("logo"),
                },
                "away": {
                    "id": f["teams"]["away"]["id"],
                    "name": f["teams"]["away"]["name"],
                    "logo": f["teams"]["away"].get("logo"),
                },
                "score": {
                    "home": goals["home"] if goals["home"] is not None else None,
                    "away": goals["away"] if goals["away"] is not None else None,
                },
            })
        # Trie par heure
        out.sort(key=lambda x: x["heure"])
        return JSONResponse({"date": target, "matchs": out})
    except Exception as e:
        return JSONResponse({"erreur": str(e)}, status_code=500)


# ===================== Live =====================

STATUTS_EN_COURS = {"1H", "HT", "2H", "ET", "BT", "P", "INT", "LIVE"}


@app.get("/api/live")
def live_matches():
    """Tous les matchs en cours dans nos ligues, temps réel (sans cache)."""
    try:
        api = ApiFootball()
        data = api.get("fixtures", {"live": "all"}, use_cache=False)
        resp = data.get("response", [])
        ids_autorises = set(IDS_SOCCER)
        out = []
        for f in resp:
            if f["league"]["id"] not in ids_autorises:
                continue
            out.append({
                "fixture_id": f["fixture"]["id"],
                "status": f["fixture"]["status"]["short"],
                "elapsed": f["fixture"]["status"].get("elapsed"),
                "ligue": f["league"]["name"],
                "ligue_logo": f["league"].get("logo"),
                "home": {
                    "id": f["teams"]["home"]["id"],
                    "name": f["teams"]["home"]["name"],
                    "logo": f["teams"]["home"].get("logo"),
                },
                "away": {
                    "id": f["teams"]["away"]["id"],
                    "name": f["teams"]["away"]["name"],
                    "logo": f["teams"]["away"].get("logo"),
                },
                "score": {
                    "home": f["goals"]["home"] if f["goals"]["home"] is not None else 0,
                    "away": f["goals"]["away"] if f["goals"]["away"] is not None else 0,
                },
            })
        return JSONResponse(out)
    except Exception as e:
        return JSONResponse({"erreur": str(e)}, status_code=500)


@app.get("/api/score/{fixture_id}")
def score_live(fixture_id: int):
    """Score + événements en temps réel d'un match (sans cache)."""
    try:
        api = ApiFootball()
        data = api.get("fixtures", {"id": fixture_id}, use_cache=False)
        resp = data.get("response", [])
        if not resp:
            raise HTTPException(status_code=404, detail="Match introuvable")
        f = resp[0]
        events = []
        for e in f.get("events", []):
            events.append({
                "elapsed": e["time"]["elapsed"],
                "extra": e["time"].get("extra"),
                "type": e["type"],
                "detail": e.get("detail"),
                "team_id": e["team"]["id"],
                "player": e["player"].get("name") if e.get("player") else None,
                "assist": e["assist"].get("name") if e.get("assist") else None,
            })
        goals = f["goals"]
        return JSONResponse({
            "fixture_id": fixture_id,
            "status": f["fixture"]["status"]["short"],
            "elapsed": f["fixture"]["status"].get("elapsed"),
            "score": {
                "home": goals["home"] if goals["home"] is not None else 0,
                "away": goals["away"] if goals["away"] is not None else 0,
            },
            "events": events,
        })
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"erreur": str(e)}, status_code=500)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
