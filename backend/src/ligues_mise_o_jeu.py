"""Liste blanche des ligues offertes par Mise-o-jeu+ (Loto-Québec).

But : ne JAMAIS analyser un match qu'on ne peut pas jouer chez Mise-o-jeu.
On mappe les compétitions que Mise-o-jeu propose vers leurs identifiants
API-Football.

⚠️ À vérifier/ajuster en regardant l'offre réelle sur miseojeuplus.espacejeux.com
   (l'offre varie selon la saison). C'est un point de départ des grandes
   compétitions soccer habituellement disponibles.
"""

# {id_api_football: "nom lisible"}
LIGUES_SOCCER = {
    1:   "Coupe du Monde",
    4:   "Euro (Championnat d'Europe)",
    2:   "Ligue des Champions (UEFA)",
    3:   "Ligue Europa (UEFA)",
    848: "Ligue Conférence (UEFA)",
    39:  "Premier League (Angleterre)",
    140: "La Liga (Espagne)",
    135: "Serie A (Italie)",
    78:  "Bundesliga (Allemagne)",
    61:  "Ligue 1 (France)",
    88:  "Eredivisie (Pays-Bas)",
    94:  "Primeira Liga (Portugal)",
    253: "MLS (États-Unis/Canada)",
    262: "Liga MX (Mexique)",
    71:  "Brasileirão Série A (Brésil)",
    128: "Liga Profesional (Argentine)",
    98:  "J1 League (Japon)",
    # Championnats actifs en été (calendrier civil) — offerts sur Mise-o-jeu
    239: "Primera A (Colombie)",
    344: "Primera División (Bolivie)",
    242: "Liga Pro Serie A (Équateur)",
    268: "Primera División (Uruguay)",
    265: "Primera División (Chili)",
    281: "Liga 1 (Pérou)",
    169: "Veikkausliiga (Finlande)",
    113: "Allsvenskan (Suède)",
    103: "Eliteserien (Norvège)",
    9:   "Copa América",
    13:  "Copa Libertadores",
    11:  "Copa Sudamericana",
    45:  "FA Cup (Angleterre)",
    143: "Copa del Rey (Espagne)",
}

# IDs uniquement (pratique pour filtrer rapidement)
IDS_SOCCER = set(LIGUES_SOCCER.keys())


def est_offert(league_id: int) -> bool:
    """Vrai si la ligue fait (probablement) partie de l'offre Mise-o-jeu."""
    return league_id in IDS_SOCCER
