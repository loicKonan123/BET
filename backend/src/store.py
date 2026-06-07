"""Persistance des tickets sauvegardés (SQLite).

Stocke les combinés que l'utilisateur garde, leur statut (en attente /
gagné / perdu) et calcule les statistiques (ROI, taux de réussite).

SQLite = zéro installation, fichier unique. Migrable vers PostgreSQL plus tard.
"""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "tickets.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

STATUTS = {"en_attente", "gagne", "perdu"}


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _conn() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS tickets (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                cree_le       TEXT NOT NULL,
                cote_totale   REAL NOT NULL,
                proba_reussite REAL NOT NULL,
                value         REAL NOT NULL,
                mise          REAL NOT NULL DEFAULT 10,
                statut        TEXT NOT NULL DEFAULT 'en_attente',
                selections    TEXT NOT NULL
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS analyses_ia (
                fixture_id  INTEGER PRIMARY KEY,
                cree_le     TEXT NOT NULL,
                data        TEXT NOT NULL
            )
            """
        )


def _row_to_dict(r: sqlite3.Row) -> dict:
    return {
        "id": r["id"],
        "cree_le": r["cree_le"],
        "cote_totale": r["cote_totale"],
        "proba_reussite": r["proba_reussite"],
        "value": r["value"],
        "mise": r["mise"],
        "statut": r["statut"],
        "selections": json.loads(r["selections"]),
    }


def sauver_ticket(combine: dict, mise: float = 10.0) -> dict:
    """Enregistre un combiné (avec ses sélections) en base."""
    with _conn() as c:
        cur = c.execute(
            """INSERT INTO tickets
               (cree_le, cote_totale, proba_reussite, value, mise, statut, selections)
               VALUES (?, ?, ?, ?, ?, 'en_attente', ?)""",
            (
                datetime.now(timezone.utc).isoformat(),
                float(combine["cote_totale"]),
                float(combine["proba_reussite"]),
                float(combine.get("value", 0)),
                float(mise),
                json.dumps(combine.get("selections", []), ensure_ascii=False),
            ),
        )
        rowid = cur.lastrowid
    return lister_un(rowid)  # après commit, sinon non visible


def lister_un(ticket_id: int) -> dict | None:
    with _conn() as c:
        r = c.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        return _row_to_dict(r) if r else None


def lister_tickets() -> list[dict]:
    with _conn() as c:
        rows = c.execute("SELECT * FROM tickets ORDER BY id DESC").fetchall()
        return [_row_to_dict(r) for r in rows]


def definir_statut(ticket_id: int, statut: str) -> dict | None:
    if statut not in STATUTS:
        raise ValueError(f"statut invalide : {statut}")
    with _conn() as c:
        c.execute("UPDATE tickets SET statut = ? WHERE id = ?", (statut, ticket_id))
    return lister_un(ticket_id)  # après commit


def supprimer_ticket(ticket_id: int) -> None:
    with _conn() as c:
        c.execute("DELETE FROM tickets WHERE id = ?", (ticket_id,))


def analytics() -> dict:
    """Statistiques globales : ROI, taux de réussite, profit."""
    tickets = lister_tickets()
    gagnes = [t for t in tickets if t["statut"] == "gagne"]
    perdus = [t for t in tickets if t["statut"] == "perdu"]
    en_attente = [t for t in tickets if t["statut"] == "en_attente"]

    regles = gagnes + perdus
    mise_totale = sum(t["mise"] for t in regles)
    gain_total = sum(t["mise"] * t["cote_totale"] for t in gagnes)
    profit = gain_total - mise_totale
    nb_regles = len(regles)

    return {
        "total": len(tickets),
        "gagnes": len(gagnes),
        "perdus": len(perdus),
        "en_attente": len(en_attente),
        "taux_reussite": round(len(gagnes) / nb_regles, 4) if nb_regles else 0.0,
        "mise_totale": round(mise_totale, 2),
        "gain_total": round(gain_total, 2),
        "profit": round(profit, 2),
        "roi": round(profit / mise_totale, 4) if mise_totale else 0.0,
    }


# ===================== Cache des analyses IA =====================

def save_analyse_ia(fixture_id: int, data: dict) -> None:
    """Stocke (ou remplace) l'analyse IA d'un match."""
    with _conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO analyses_ia (fixture_id, cree_le, data) VALUES (?, ?, ?)",
            (fixture_id, datetime.now(timezone.utc).isoformat(),
             json.dumps(data, ensure_ascii=False)),
        )


def get_analyse_ia(fixture_id: int) -> dict | None:
    """Renvoie l'analyse IA en cache (permanente : calculée une fois, stable).

    L'analyse ne change pas d'une visite à l'autre. Pour la recalculer,
    l'appelant passe force=1 (qui ignore le cache et réécrit).
    """
    with _conn() as c:
        r = c.execute(
            "SELECT cree_le, data FROM analyses_ia WHERE fixture_id = ?", (fixture_id,)
        ).fetchone()
    if not r:
        return None
    d = json.loads(r["data"])
    d["cache"] = True
    d["cree_le"] = r["cree_le"]
    return d
