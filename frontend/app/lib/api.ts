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

export type Joueur = { numero: number | null; nom: string; poste: string | null };

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
