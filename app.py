"""Petit serveur web : page HTML + bouton qui génère le ticket.

Lancer :
    python app.py
Puis ouvrir http://127.0.0.1:8000

L'endpoint /api/generer fait tourner le pipeline et renvoie le JSON
(combinés + analyses). Grâce au cache disque, recliquer ne reconsomme
pas le quota API.
"""
from datetime import date, timedelta
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse

from src.api_client import ApiFootball
from src.ligues_mise_o_jeu import IDS_SOCCER, LIGUES_SOCCER
from src.pipeline import fixtures_depuis_reponse, generer_pronostics

app = FastAPI(title="BET — Générateur de tickets")

WEB_DIR = Path(__file__).resolve().parent / "web"


@app.get("/")
def index():
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/ligues")
def ligues():
    """Liste blanche des ligues offertes par Mise-o-jeu (validateur)."""
    return [{"id": lid, "nom": nom} for lid, nom in LIGUES_SOCCER.items()]


def _fenetre_dates(rayon: int = 1) -> list[str]:
    """Dates accessibles : aujourd'hui ± rayon (le plan gratuit limite à J±1)."""
    today = date.today()
    return [(today + timedelta(days=i)).isoformat() for i in range(-rayon, rayon + 1)]


@app.get("/api/generer")
def generer(
    nb_tickets: int = 3,
    cote_cible: float = 3.0,
    stats_season: int = 2024,   # plan gratuit ; saison courante avec une clé prod
    max_matchs: int = 12,
    valider: int = 1,           # 1 = liste blanche Mise-o-jeu ; 0 = tous (démo hors-saison)
):
    """Scan AUTOMATIQUE : parcourt tous les matchs des championnats Mise-o-jeu
    sur toutes les dates accessibles, et génère les tickets. Aucun choix manuel.
    """
    try:
        api = ApiFootball()
        autorisees = IDS_SOCCER if valider else None

        fixtures = []
        dates_ok = []
        for d in _fenetre_dates():
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


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
