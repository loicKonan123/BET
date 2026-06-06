"""Vérifie que la clé API fonctionne et affiche le quota restant."""
import sys

sys.stdout.reconfigure(encoding="utf-8")

from src.api_client import ApiFootball


def main():
    api = ApiFootball()
    data = api.status()
    resp = data.get("response", {})

    account = resp.get("account", {})
    subscription = resp.get("subscription", {})
    requests_info = resp.get("requests", {})

    print("=" * 50)
    print("CLÉ API VALIDE ✔")
    print("=" * 50)
    print(f"Compte      : {account.get('firstname', '?')} {account.get('lastname', '')}".strip())
    print(f"Email       : {account.get('email', '?')}")
    print(f"Plan        : {subscription.get('plan', '?')}")
    print(f"Actif       : {subscription.get('active', '?')}")
    print(f"Fin         : {subscription.get('end', '?')}")
    print("-" * 50)
    print(f"Requêtes utilisées aujourd'hui : {requests_info.get('current', '?')}")
    print(f"Limite quotidienne             : {requests_info.get('limit_day', '?')}")
    print("=" * 50)


if __name__ == "__main__":
    main()
