"""Petit serveur web : page HTML + bouton qui génère le ticket.

Lancer :
    python app.py
Puis ouvrir http://127.0.0.1:8000

L'endpoint /api/generer fait tourner le pipeline et renvoie le JSON
(combinés + analyses). Grâce au cache disque, recliquer ne reconsomme
pas le quota API.
"""
from datetime import date, timedelta

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src import store
from src.analyste import analyser_avec_ia
from src.api_client import ApiFootball
from src.ligues_mise_o_jeu import IDS_SOCCER, LIGUES_SOCCER
from src.pipeline import (
    analyser_fixture,
    analyser_fixture_sans_cotes,
    conseil_de_paris,
    fixtures_depuis_reponse,
    generer_pronostics,
)

app = FastAPI(title="BET — API")
store.init_db()

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


def _fenetre_dates(jours_avant: int = 7) -> list[str]:
    """Dates à scanner : aujourd'hui + les `jours_avant` prochains jours."""
    today = date.today()
    return [(today + timedelta(days=i)).isoformat() for i in range(0, jours_avant + 1)]


def _scanner_fixtures(api, jours: int, valider: int, max_matchs: int):
    """Récupère les matchs jouables sur la fenêtre de dates. -> (fixtures, dates_ok)."""
    autorisees = IDS_SOCCER if valider else None
    fixtures, dates_ok = [], []
    for d in _fenetre_dates(jours):
        try:
            data = api.get("fixtures", {"date": d})
        except Exception:
            continue
        dates_ok.append(d)
        fixtures += fixtures_depuis_reponse(
            data.get("response", []), ligues_autorisees=autorisees
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
    """Scan AUTOMATIQUE : génère les tickets sur les matchs jouables Mise-o-jeu."""
    try:
        api = ApiFootball()
        fixtures, dates_ok = _scanner_fixtures(api, jours, valider, max_matchs)
        resultat = generer_pronostics(
            api, fixtures,
            nb_combines=nb_tickets,
            cote_cible=cote_cible,
            stats_season=stats_season,
        )
        resultat["dates_scannees"] = dates_ok
        resultat["validateur_mise_o_jeu"] = bool(valider)
        return JSONResponse(resultat)
    except Exception as e:
        return JSONResponse({"erreur": str(e)}, status_code=500)


@app.get("/api/analyses")
def analyses(
    stats_season: int | None = None,
    max_matchs: int = 40,
    valider: int = 1,
    jours: int = 7,
):
    """Liste des matchs jouables analysés (probas + forme), pour la page Analyses."""
    try:
        api = ApiFootball()
        fixtures, dates_ok = _scanner_fixtures(api, jours, valider, max_matchs)
        out = []
        for fx in fixtures:
            r = analyser_fixture_sans_cotes(api, fx, stats_season=stats_season)
            if r:
                out.append(r)
        return JSONResponse({"dates_scannees": dates_ok, "nb": len(out), "analyses": out})
    except Exception as e:
        return JSONResponse({"erreur": str(e)}, status_code=500)


def _detail_match(api, fixture_id: int, stats_season: int | None = None) -> dict:
    """Construit le détail complet d'un match (probas, value, conseil, équipes)."""
    data = api.get("fixtures", {"id": fixture_id})
    resp = data.get("response", [])
    if not resp:
        raise HTTPException(status_code=404, detail="Match introuvable")
    f = resp[0]
    fx = fixtures_depuis_reponse([f])[0]

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
    return res


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
def match_ia(fixture_id: int, stats_season: int | None = None):
    """Analyse fine par le cerveau LLM (DeepSeek) — à la demande."""
    try:
        api = ApiFootball()
        detail = _detail_match(api, fixture_id, stats_season)
        return JSONResponse(analyser_avec_ia(api, detail))
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"erreur": str(e)}, status_code=500)


# ===================== Tickets sauvegardés (history) =====================

class SelectionIn(BaseModel):
    match: str
    ligue: str = ""
    marche: str
    cote: float
    proba: float


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


@app.get("/api/analytics")
def get_analytics():
    return store.analytics()


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
