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
