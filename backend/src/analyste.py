"""Analyse football argumentée à partir d'un dossier de données traçables.

Le LLM explique le consensus commun. Il ne modifie aucune probabilite.
"""
import json
import logging
import math
import os
import re
from datetime import datetime, timezone
from time import perf_counter

from openai import OpenAI

from .api_client import ApiFootball
from .analyse_editoriale import INSTRUCTION as _INSTRUCTION, SYSTEME as _SYSTEME
from .analyse_editoriale import VERSION_ANALYSE, valider_analyse
from .blend import valider_1x2

BASE_URL = "https://api.deepseek.com"
log = logging.getLogger("edge.ia")

LIB_1X2 = {"1": "Victoire domicile", "X": "Match nul", "2": "Victoire extérieur"}


def _fusion_equipe(p_ia, p_cons, poids_consensus=1.0):
    """Compatibilite : seul le consensus statistique fait autorite."""
    return valider_1x2(p_cons)

# Nations hôtes du Mondial 2026 (terrain réel = domicile, pas neutre)
HOTES_WC_2026 = {2, 16, 101}  # USA, Mexico, Canada

# Compétitions de sélections nationales
LIGUES_NATIONALES = {1, 4, 5, 9, 10, 29, 30, 31, 32, 33, 34}


def _client(rapide: bool = False) -> OpenAI:
    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY manquante (vérifie backend/.env)")
    return OpenAI(api_key=key, base_url=BASE_URL,
                  timeout=60.0 if rapide else 300.0,
                  max_retries=0 if rapide else 1)


def _blessures(api: ApiFootball, fixture_id: int, home_id: int, away_id: int) -> dict:
    out = {"domicile": [], "exterieur": [], "statut": "indisponible"}
    try:
        data = api.get("injuries", {"fixture": fixture_id}, ttl=3600)
    except Exception:
        return out
    out["statut"] = "absences_renseignees" if data.get("response") else "aucune_absence_renseignee"
    out["limite"] = "La couverture peut être incomplète ; une liste vide ne prouve pas un effectif complet."
    for item in data.get("response", []):
        joueur = item.get("player", {})
        team_id = item.get("team", {}).get("id")
        ligne = f"{joueur.get('name', '?')} ({joueur.get('reason', '?')})"
        if team_id == home_id:
            out["domicile"].append(ligne)
        elif team_id == away_id:
            out["exterieur"].append(ligne)
    return out


def _h2h(api: ApiFootball, home_id: int, away_id: int, n: int = 5) -> list[str]:
    try:
        data = api.get("fixtures/headtohead", {"h2h": f"{home_id}-{away_id}", "last": n})
    except Exception:
        return []
    out = []
    for f in data.get("response", []):
        h = f["teams"]["home"]
        a = f["teams"]["away"]
        gh = f.get("goals", {}).get("home")
        ga = f.get("goals", {}).get("away")
        date = f.get("fixture", {}).get("date", "")[:10]
        out.append(f"{h['name']} {gh}-{ga} {a['name']} ({date})")
    return out


def _rangs_equipes(classement: dict | None, home_id: int, away_id: int) -> dict | None:
    if not classement:
        return None
    out = {}
    for groupe in classement.get("groupes", []):
        for l in groupe.get("lignes", []):
            if l.get("equipe_id") == home_id:
                out["domicile"] = {"rang": l.get("rang"), "points": l.get("points"),
                                   "joues": l.get("joues"), "forme": l.get("forme")}
            elif l.get("equipe_id") == away_id:
                out["exterieur"] = {"rang": l.get("rang"), "points": l.get("points"),
                                    "joues": l.get("joues"), "forme": l.get("forme")}
    return out or None


def _resume_forme(forme: str) -> dict:
    f = (forme or "").upper()
    v, n, d = f.count("W"), f.count("D"), f.count("L")
    return {
        "bilan": f"{v}V {n}N {d}D sur {len(f)} derniers" if f else "données insuffisantes",
        "sequence": f"{f} (gauche=ancien, droite=récent)" if f else None,
    }


def _contexte_tournoi(detail: dict) -> dict:
    """Construit le contexte qualitatif du tournoi pour l'IA."""
    league_id = detail.get("league_id", 0)
    home_id = detail.get("home", {}).get("id", 0)
    away_id = detail.get("away", {}).get("id", 0)
    round_str = detail.get("round", "")

    ctx = {
        "competition": detail.get("ligue", ""),
        "phase": round_str,
        "est_competition_nationale": league_id in LIGUES_NATIONALES,
    }

    # Détecte si une équipe joue sur son propre territoire (WC host)
    if league_id == 1:  # Coupe du Monde
        if home_id in HOTES_WC_2026:
            ctx["terrain"] = f"L'équipe à domicile ({detail.get('home', {}).get('name', '')}) est NATION HÔTE du Mondial 2026 — avantage réel de terrain (public, habitudes, pression)."
        elif away_id in HOTES_WC_2026:
            ctx["terrain"] = f"L'équipe à l'extérieur ({detail.get('away', {}).get('name', '')}) est NATION HÔTE mais joue en déplacement relatif."
        else:
            ctx["terrain"] = "Terrain neutre (Mondial 2026, aucune des deux équipes n'est nation hôte)."
    else:
        ctx["terrain"] = "Match sur terrain officiel (avantage domicile standard)."

    return ctx


def _stats_detaillees(detail: dict) -> dict | None:
    """Extrait les stats dom/ext séparées si présentes dans le détail."""
    ba = detail.get("buts_attendus")
    if not ba:
        return None
    return {
        "buts_attendus_poisson": ba,
        "note": "Ces valeurs intègrent les stats historiques dom/ext séparées des deux équipes.",
    }


def _bloc_multi_modeles(mm: dict | None) -> dict | None:
    """Met en forme la vue multi-modèles (Poisson + Elo + marché + consensus)."""
    if not mm:
        return None
    cons = mm.get("consensus", {})
    return {
        "poisson_1x2": mm.get("poisson"),
        "elo_1x2": mm.get("elo"),
        "elo_details": mm.get("elo_info"),
        "ml_1x2": mm.get("ml"),
        "dynamique_1x2": mm.get("dynamique"),
        "contextuel_1x2": mm.get("contextuel"),
        "xg_simple_1x2": mm.get("xg_simple"),
        "validation": mm.get("validation"),
        "provenance_cotes": mm.get("provenance_cotes"),
        "version_modele": mm.get("version_modele"),
        "marche_1x2_sans_vig": mm.get("marche"),
        "consensus_pondere": cons.get("probabilites"),
        "poids_consensus": cons.get("poids_utilises"),
        "accord_entre_sources": cons.get("accord"),
        "diagnostic_confluence": cons.get("diagnostic"),
        "note": (
            "Sources potentiellement corrélées, fusionnées par pool logarithmique. "
            "Le ML est absent s'il n'est pas prêt. Le marché est un instantané, "
            "pas une closing line certifiée. 'accord' mesure l'écart maximal sur "
            "les trois issues (bas = proximité, pas certitude ; null = non mesurable)."
        ),
    }


def _historique_avant(matchs: list, date_match: str | None) -> list:
    """Évite de raconter le résultat du match étudié comme une preuve préalable."""
    def date_utc(value):
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

    try:
        limite = date_utc(date_match)
    except (AttributeError, TypeError, ValueError):
        return []
    retenus = []
    for match in matchs or []:
        try:
            if date_utc(match.get("date")) < limite:
                retenus.append(match)
        except (AttributeError, TypeError, ValueError):
            continue
    return sorted(retenus, key=lambda m: date_utc(m["date"]), reverse=True)


def _reperes_marche(detail: dict) -> list[dict]:
    """Calculs de prix déterministes : le rédacteur n'a pas à les improviser."""
    p = valider_1x2(((detail.get("multi_modeles") or {}).get("consensus") or {}).get("probabilites"))
    if not p:
        return []
    probas = {**p, "1X": p["1"] + p["X"], "X2": p["X"] + p["2"], "12": p["1"] + p["2"], **detail.get("probabilites", {})}
    cotes = {s.get("cle"): s.get("cote") for s in detail.get("selections", [])}
    out = []
    for cle, proba in probas.items():
        cote = cotes.get(cle)
        valide = (not isinstance(cote, bool) and isinstance(cote, (int, float))
                  and math.isfinite(cote) and cote > 1)
        out.append({
            "cle": cle, "source_proba": "consensus statistique", "proba": round(proba, 4),
            "cote_juste": round(1 / proba, 3) if proba > 0 else None,
            "cote_disponible": cote if valide else None,
            "esperance_theorique": round(proba * cote - 1, 4) if valide else None,
        })
    return out


def collecter_dossier(api: ApiFootball, detail: dict) -> dict:
    """Assemble le dossier complet : Poisson + H2H + forme + classement + contexte."""
    home = detail["home"]
    away = detail["away"]
    fixture_id = detail["fixture_id"]

    return {
        "match": detail["match"],
        "fixture_id": fixture_id,
        "date": detail.get("date"),
        "statut_match": detail.get("status"),
        "collecte_dossier_utc": datetime.now(timezone.utc).isoformat(),
        "limite_temporelle": "Données collectées au moment de la demande. Ce dossier ne constitue pas un backtest pré-match.",
        "contexte_tournoi": _contexte_tournoi(detail),
        "reference_statistique_edge": {
            "buts_attendus": detail.get("buts_attendus"),
            "probabilites_communes": detail.get("probabilites", {}),
            "note": (
                "Probabilités du moteur EDGE commun, issues d'une grille de scores alignée sur le consensus. "
                "Buts attendus par le modèle, pas xG observés tir par tir."
            ),
        },
        "modeles_multiples": _bloc_multi_modeles(detail.get("multi_modeles")),
        "forme_recente": {
            "domicile": _resume_forme(detail["forme"]["domicile"]),
            "exterieur": _resume_forme(detail["forme"]["exterieur"]),
        },
        "classement": _rangs_equipes(detail.get("classement"), home["id"], away["id"]),
        "blessures": _blessures(api, fixture_id, home["id"], away["id"]),
        "confrontations_directes": _historique_avant(detail.get("h2h", []), detail.get("date")),
        "derniers_matchs": {
            "domicile": _historique_avant(detail.get("derniers_matchs_dom", []), detail.get("date")),
            "exterieur": _historique_avant(detail.get("derniers_matchs_ext", []), detail.get("date")),
        },
        "compositions_disponibles": detail.get("compos") or [],
        "reperes_marche": _reperes_marche(detail),
        "donnees_non_fournies": [
            "Statistiques de pressing, possession et qualité des occasions tir par tir",
            "Impact chiffré des absents et compositions probables si les officielles manquent",
            "Météo, informations d'entraînement et intentions de rotation",
        ],
        "cotes_et_marches": [
            {"marche": s["marche"], "proba_edge": s["proba"],
             "cote": s.get("cote"), "value": s.get("value")}
            for s in detail.get("selections", [])
        ],
    }


def _extraire_json(texte: str) -> dict:
    texte = texte.strip()
    try:
        return json.loads(texte)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{.*\}", texte, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    return {
        "probabilites_ia": None,
        "prediction": None,
        "confiance": None,
        "analyse": texte,
        "points_cles": [],
        "facteurs_correctifs_vs_poisson": [],
        "recommandation": None,
    }


def analyser_avec_ia(api: ApiFootball, detail: dict) -> dict:
    """Construit le dossier, interroge DeepSeek, renvoie l'analyse complète."""
    t0 = perf_counter()
    dossier = collecter_dossier(api, detail)
    modele = os.getenv("DEEPSEEK_MODEL", "deepseek-reasoner")
    mode = os.getenv("DEEPSEEK_ANALYSIS_MODE", "rapide").strip().lower()
    if mode not in {"rapide", "approfondi"}:
        raise ValueError("DEEPSEEK_ANALYSIS_MODE doit être rapide ou approfondi.")
    rapide = mode == "rapide"
    # Les anciens alias imposaient leur mode ; utiliser le modèle actuel qui
    # permet de désactiver explicitement le raisonnement pour la rédaction.
    if rapide and modele in {"deepseek-reasoner", "deepseek-chat"}:
        modele = "deepseek-v4-flash"
    # Le reasoner doit disposer de place pour réfléchir ET rédiger le JSON.
    plafond = 8192 if modele == "deepseek-chat" else 65536
    try:
        max_tokens = int(os.getenv("DEEPSEEK_MAX_TOKENS", str(8192 if rapide else min(32768, plafond))))
    except ValueError as exc:
        raise ValueError("DEEPSEEK_MAX_TOKENS doit être un entier positif.") from exc
    if not 1 <= max_tokens <= plafond:
        raise ValueError(f"DEEPSEEK_MAX_TOKENS doit être compris entre 1 et {plafond} pour cette configuration.")
    if rapide:
        max_tokens = min(max_tokens, 8192)
    log.info("dossier IA fixture=%s prêt en %.2fs",
             detail.get("fixture_id"), perf_counter() - t0)

    client = _client(rapide=rapide)
    messages = [
        {"role": "system", "content": _SYSTEME},
        {"role": "user", "content": _INSTRUCTION + json.dumps(dossier, ensure_ascii=False, indent=2)},
    ]
    budgets = [max_tokens]
    if not rapide and max_tokens < plafond:
        budgets.append(min(plafond, max(32768, max_tokens * 2)))
    for tentative, budget in enumerate(budgets, start=1):
        t_llm = perf_counter()
        resp = client.chat.completions.create(
            model=modele,
            messages=messages,
            max_tokens=budget,
            response_format={"type": "json_object"},
            **({"extra_body": {"thinking": {"type": "disabled"}}} if rapide else {}),
        )
        log.info("DeepSeek fixture=%s modèle=%s tentative=%s max_tokens=%s fin=%s en %.2fs",
                 detail.get("fixture_id"), modele, tentative, budget,
                 resp.choices[0].finish_reason, perf_counter() - t_llm)
        if resp.choices[0].finish_reason != "length":
            break
        if tentative < len(budgets):
            log.warning("IA fixture=%s tronquée : nouvelle génération avec %s tokens, dossier réutilisé",
                        detail.get("fixture_id"), budgets[tentative])
    else:
        raise ValueError("L’analyse n’a pas pu être terminée dans la limite de génération. "
                         "Veuillez réessayer dans quelques instants.")
    contenu = resp.choices[0].message.content or ""
    payload = _extraire_json(contenu)
    canonique = ((detail.get("multi_modeles") or {}).get("consensus") or {}).get("probabilites")
    if canonique:
        payload["probabilites_ia"] = dict(zip(("victoire_domicile", "nul", "victoire_exterieur"),
                                             (canonique[k] for k in ("1","X","2"))))
    resultat = valider_analyse(payload)
    resultat["version_analyse"] = VERSION_ANALYSE
    resultat["modele"] = modele
    resultat["mode_generation"] = mode
    resultat["dossier"] = dossier

    # Le moteur commun est seul responsable des probabilites.
    mm = detail.get("multi_modeles") or {}
    finales = (mm.get("consensus") or {}).get("probabilites")
    resultat["probabilites_finales"] = finales
    resultat["prediction_id"] = detail.get("prediction_id")
    resultat["version_modele"] = detail.get("version_modele")
    resultat["probabilites_ia"] = None
    if finales:
        cle = max(finales, key=finales.get)
        resultat["prediction_equipe"] = LIB_1X2[cle]
        resultat["confiance_finale"] = "moyenne" if finales[cle] >= 0.50 else "faible"

    return resultat
