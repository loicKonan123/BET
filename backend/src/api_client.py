"""Client minimal pour API-Football (endpoint direct api-sports.io).

Plan gratuit : 100 requêtes / jour. On compte donc chaque appel et on
met en cache sur disque pour ne pas gaspiller le quota pendant les tests.
"""
import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

# Charge backend/.env quel que soit le répertoire de lancement
BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")

BASE_URL = "https://v3.football.api-sports.io"
CACHE_DIR = BACKEND_DIR / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


class ApiFootball:
    def __init__(self, key: str | None = None):
        self.key = key or os.getenv("API_FOOTBALL_KEY")
        if not self.key:
            raise RuntimeError("API_FOOTBALL_KEY manquante (vérifie le fichier .env)")
        self.session = requests.Session()
        self.session.headers.update({"x-apisports-key": self.key})

    def _cache_path(self, endpoint: str, params: dict) -> Path:
        slug = endpoint.strip("/").replace("/", "_")
        if params:
            slug += "_" + "_".join(f"{k}-{v}" for k, v in sorted(params.items()))
        return CACHE_DIR / f"{slug}.json"

    def get(self, endpoint: str, params: dict | None = None, use_cache: bool = True) -> dict:
        params = params or {}
        cache_file = self._cache_path(endpoint, params)
        if use_cache and cache_file.exists():
            return json.loads(cache_file.read_text(encoding="utf-8"))

        url = f"{BASE_URL}/{endpoint.lstrip('/')}"

        # Gère la limite par minute du plan gratuit (429) : attend et réessaie
        max_essais = 4
        for essai in range(max_essais):
            resp = self.session.get(url, params=params, timeout=20)
            if resp.status_code == 429:
                attente = int(resp.headers.get("Retry-After", 0)) or 65
                print(f"  [rate-limit] limite/minute atteinte, attente {attente}s "
                      f"(essai {essai + 1}/{max_essais})...")
                time.sleep(attente)
                continue
            resp.raise_for_status()
            break
        else:
            raise RuntimeError("Limite de requêtes dépassée malgré les tentatives.")

        data = resp.json()

        # API-Football renvoie les erreurs dans le corps, pas en code HTTP
        if data.get("errors"):
            raise RuntimeError(f"Erreur API : {data['errors']}")

        cache_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        time.sleep(0.3)  # plan PRO ~300 req/min -> ~200/min, marge confortable
        return data

    def status(self) -> dict:
        """Vérifie la clé et renvoie le quota restant."""
        return self.get("status", use_cache=False)
