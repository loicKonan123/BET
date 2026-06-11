// URL du backend FastAPI (configurable via .env.local)
export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export type Selection = {
  match: string;
  ligue: string;
  marche: string;
  cote: number;
  proba: number;
  fixture_id?: number;
  cle?: string;
};

export type Combine = {
  cote_totale: number;
  proba_reussite: number;
  value: number;
  selections: Selection[];
};

export type Analyse = {
  match: string;
  ligue: string;
  fixture_id: number;
  date?: string;
  status?: string;
  buts_attendus: { domicile: number; exterieur: number };
  forme: { domicile: string; exterieur: string };
  probabilites: Record<string, number>;
};

export type Resultat = {
  genere_le: string;
  nb_matchs_analyses: number;
  nb_combines: number;
  dates_scannees?: string[];
  combines: Combine[];
  analyses: Analyse[];
  erreur?: string;
};

// ---- Analyses (liste) ----
export async function getAnalyses(): Promise<{
  dates_scannees: string[];
  nb: number;
  analyses: Analyse[];
  erreur?: string;
}> {
  const r = await fetch(`${API_URL}/api/analyses`);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

// ---- Détail d'un match ----
export type MarketSelection = {
  cle: string;
  marche: string;
  proba: number;
  cote: number;
  proba_implicite: number;
  value: number;
  est_value_bet: boolean;
};

export type Conseil = {
  marche: string;
  proba: number;
  cote: number | null;
  value: number;
  raison: string;
};

export type LigneClassement = {
  rang: number | null;
  equipe_id: number;
  equipe: string;
  logo: string | null;
  points: number | null;
  joues: number | null;
  diff: number | null;
  forme: string | null;
};

export type GroupeClassement = {
  nom: string;
  lignes: LigneClassement[];
};

export type Classement = {
  groupes: GroupeClassement[];
  home_id: number;
  away_id: number;
};

export type DernierMatch = {
  date: string;
  domicile: string;
  exterieur: string;
  score: string;
  resultat: "W" | "D" | "L";
  a_domicile: boolean;
};

export type Joueur = { id?: number; numero: number | null; nom: string; poste: string | null; grid?: string };

export type H2HMatch = {
  date: string;
  domicile: string;
  exterieur: string;
  score: string;
  home_id: number;
};

export type CompoEquipe = {
  equipe: string;
  logo?: string;
  formation?: string;
  titulaires: Joueur[];
  remplacants: Joueur[];
};

export type MatchDetail = Analyse & {
  date: string;
  home: { id: number; name: string; logo?: string };
  away: { id: number; name: string; logo?: string };
  selections: MarketSelection[];
  conseil: Conseil | null;
  classement: Classement | null;
  derniers_matchs_dom: DernierMatch[];
  derniers_matchs_ext: DernierMatch[];
  compos: CompoEquipe[];
  h2h: H2HMatch[];
  erreur?: string;
};

export async function getMatch(fixtureId: number): Promise<MatchDetail> {
  const r = await fetch(`${API_URL}/api/match/${fixtureId}`);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

// ---- Analyse IA (cerveau DeepSeek) ----
export type AnalyseIA = {
  analyse: string;
  points_cles: string[];
  facteurs_risque: string[];
  recommandation: { marche: string; confiance: string; justification: string } | null;
  accord_avec_modele: boolean | null;
  nuance: string;
  modele: string;
  cache?: boolean;
  cree_le?: string;
  erreur?: string;
};

export async function getAnalyseIA(fixtureId: number, force = false): Promise<AnalyseIA> {
  const r = await fetch(`${API_URL}/api/match/${fixtureId}/ia${force ? "?force=1" : ""}`);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

export async function genererTickets(nb: number): Promise<Resultat> {
  const r = await fetch(`${API_URL}/api/generer?nb_tickets=${nb}`);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

// ---- Persistance des tickets (history) ----
export type TicketEnregistre = Combine & {
  id: number;
  cree_le: string;
  statut: "en_attente" | "gagne" | "perdu";
};

export async function sauverTicket(c: Combine): Promise<TicketEnregistre> {
  const r = await fetch(`${API_URL}/api/tickets`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(c),
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

export async function listerTickets(): Promise<TicketEnregistre[]> {
  const r = await fetch(`${API_URL}/api/tickets`);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

export async function definirResultat(
  id: number,
  statut: "gagne" | "perdu" | "en_attente"
): Promise<TicketEnregistre> {
  const r = await fetch(`${API_URL}/api/tickets/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ statut }),
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

export async function supprimerTicket(id: number): Promise<void> {
  const r = await fetch(`${API_URL}/api/tickets/${id}`, { method: "DELETE" });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
}

export async function settlerTickets(): Promise<{ settled: number; skipped: number }> {
  const r = await fetch(`${API_URL}/api/tickets/settle`, { method: "POST" });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

export type Analytics = {
  total: number;
  gagnes: number;
  perdus: number;
  en_attente: number;
  taux_reussite: number;
};

export async function getAnalytics(): Promise<Analytics> {
  const r = await fetch(`${API_URL}/api/analytics`);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

// ---- Backtest ----
export type BacktestMatch = {
  fixture_id: number; match: string; date: string; score: string;
  pred_1x2: string;    reel_1x2: string;    bon_1x2: boolean;
  pred_over25: string; reel_over25: string; bon_over25: boolean;
  pred_over15: string; reel_over15: string; bon_over15: boolean;
  pred_btts: string;   reel_btts: string;   bon_btts: boolean;
  pred_dc_12: string;  bon_dc_12: boolean;
  pred_dc_1x: string;  bon_dc_1x: boolean;
  lam_dom: number; lam_ext: number;
};

export type BacktestResult = {
  league_id: number; ligue: string; saison: number; total_matches: number;
  accuracy_1x2: number; ok_1x2: number;
  accuracy_over25: number;  ok_over25: number;  n_over25: number;
  accuracy_under25: number; ok_under25: number; n_under25: number;
  accuracy_over15: number;  ok_over15: number;  n_over15: number;
  accuracy_under15: number; ok_under15: number; n_under15: number;
  accuracy_btts_oui: number; ok_btts_oui: number; n_btts_oui: number;
  accuracy_btts_non: number; ok_btts_non: number; n_btts_non: number;
  accuracy_dc_12: number; ok_dc_12: number; n_dc_12: number;
  accuracy_dc_1x: number; ok_dc_1x: number; n_dc_1x: number;
  matchs: BacktestMatch[];
};

// ---- Équipe ----
export type TeamMatch = {
  fixture_id: number;
  date: string;
  ligue: string;
  ligue_logo?: string;
  adversaire_id: number;
  adversaire: string;
  adversaire_logo?: string;
  a_domicile: boolean;
  score: string;
  resultat: "W" | "D" | "L";
  buts_pour: number;
  buts_contre: number;
};

export type TeamDetail = {
  id: number;
  nom: string;
  logo?: string;
  pays?: string;
  stade?: string;
  ville?: string;
  stats: {
    matchs: number;
    victoires: number;
    nuls: number;
    defaites: number;
    buts_pour: number;
    buts_contre: number;
    moy_bp: number;
    moy_bc: number;
  };
  forme: string;
  matchs: TeamMatch[];
};

export async function getTeam(teamId: number): Promise<TeamDetail> {
  const r = await fetch(`${API_URL}/api/team/${teamId}`);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

// ---- Joueur ----
export type PlayerDetail = {
  id: number;
  nom: string;
  prenom?: string;
  nom_famille?: string;
  photo?: string;
  nationalite?: string;
  naissance?: string;
  taille?: string;
  poids?: string;
  poste?: string;
  equipe_id?: number;
  equipe?: string;
  equipe_logo?: string;
  saison: number;
  stats: {
    matchs: number;
    titularisations: number;
    minutes: number;
    buts: number;
    passes_decisives: number;
    cartons_jaunes: number;
    cartons_rouges: number;
    passes: number;
    note?: string;
  };
};

export async function getPlayer(playerId: number): Promise<PlayerDetail> {
  const r = await fetch(`${API_URL}/api/player/${playerId}`);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

// ---- Live ----
export type LiveMatch = {
  fixture_id: number;
  status: string;
  elapsed: number | null;
  ligue: string;
  ligue_logo?: string;
  home: { id: number; name: string; logo?: string };
  away: { id: number; name: string; logo?: string };
  score: { home: number; away: number };
};

export type LiveEvent = {
  elapsed: number;
  extra?: number;
  type: string;   // "Goal" | "Card" | "subst" | "Var"
  detail?: string;
  team_id: number;
  player?: string;
  assist?: string;
};

export type LiveScore = {
  fixture_id: number;
  status: string;
  elapsed: number | null;
  score: { home: number; away: number };
  events: LiveEvent[];
};

// ---- Scores (navigation par date) ----
export type ScoreMatch = {
  fixture_id: number;
  status: string;
  elapsed: number | null;
  heure: string;
  ligue_id: number;
  ligue: string;
  ligue_logo?: string;
  home: { id: number; name: string; logo?: string };
  away: { id: number; name: string; logo?: string };
  score: { home: number | null; away: number | null };
};

export type ScoresJour = {
  date: string;
  matchs: ScoreMatch[];
};

export async function getScores(date: string): Promise<ScoresJour> {
  const r = await fetch(`${API_URL}/api/scores?date_str=${date}`);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

export async function getLiveMatches(): Promise<LiveMatch[]> {
  const r = await fetch(`${API_URL}/api/live`);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

export async function getLiveScore(fixtureId: number): Promise<LiveScore> {
  const r = await fetch(`${API_URL}/api/score/${fixtureId}`);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

export async function runBacktest(
  league: number,
  season: number,
  limit: number = 0
): Promise<BacktestResult> {
  const r = await fetch(
    `${API_URL}/api/backtest?league=${league}&season=${season}&limit=${limit}`
  );
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}
