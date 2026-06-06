// URL du backend FastAPI (configurable via .env.local)
export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export type Selection = {
  match: string;
  ligue: string;
  marche: string;
  cote: number;
  proba: number;
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

export type MatchDetail = Analyse & {
  date: string;
  home: { id: number; name: string; logo?: string };
  away: { id: number; name: string; logo?: string };
  selections: MarketSelection[];
  conseil: Conseil | null;
  erreur?: string;
};

export async function getMatch(fixtureId: number): Promise<MatchDetail> {
  const r = await fetch(`${API_URL}/api/match/${fixtureId}`);
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
  mise: number;
};

export async function sauverTicket(c: Combine, mise = 10): Promise<TicketEnregistre> {
  const r = await fetch(`${API_URL}/api/tickets`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...c, mise }),
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

export type Analytics = {
  total: number;
  gagnes: number;
  perdus: number;
  en_attente: number;
  taux_reussite: number;
  mise_totale: number;
  gain_total: number;
  profit: number;
  roi: number;
};

export async function getAnalytics(): Promise<Analytics> {
  const r = await fetch(`${API_URL}/api/analytics`);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}
