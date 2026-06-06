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
from src.api_client import ApiFootball
from src.ligues_mise_o_jeu import IDS_SOCCER, LIGUES_SOCCER
from src.pipeline import fixtures_depuis_reponse, generer_pronostics

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
    """Dates à scanner : aujourd'hui + les `jours_avant` prochains jours.

    (Le plan PRO retire la limite J±1 du plan gratuit.)
    """
    today = date.today()
    return [(today + timedelta(days=i)).isoformat() for i in range(0, jours_avant + 1)]


@app.get("/api/generer")
def generer(
    nb_tickets: int = 3,
    cote_cible: float = 3.0,
    stats_season: int | None = None,  # None = saison réelle de chaque match (PRO)
    max_matchs: int = 30,
    valider: int = 1,           # 1 = liste blanche Mise-o-jeu ; 0 = tous
    jours: int = 7,             # nombre de jours à venir à scanner
):
    """Scan AUTOMATIQUE : parcourt tous les matchs des championnats Mise-o-jeu
    sur toutes les dates accessibles, et génère les tickets. Aucun choix manuel.
    """
    try:
        api = ApiFootball()
        autorisees = IDS_SOCCER if valider else None

        fixtures = []
        dates_ok = []
        for d in _fenetre_dates(jours):
            try:
                data = api.get("fixtures", {"date": d})
            except Exception:
                continue  # date hors quota gratuit -> on saute
            dates_ok.append(d)
            fixtures += fixtures_depuis_reponse(
                data.get("response", []), ligues_autorisees=autorisees
            )

        fixtures = fixtures[:max_matchs]
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
