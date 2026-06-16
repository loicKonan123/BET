"use client";

import { useEffect, useState } from "react";
import Icon from "../components/Icon";
import {
  TicketPremium,
  genererPremium,
  listerPremium,
  definirResultatPremium,
  supprimerPremium,
} from "../lib/api";
import { dateHeureCanada } from "../lib/date";

const COTES = [3, 5, 10];

const BADGE: Record<string, string> = {
  en_attente: "bg-tertiary/20 text-tertiary",
  gagne: "bg-primary/20 text-primary",
  perdu: "bg-error/20 text-error",
};
const LABEL: Record<string, string> = {
  en_attente: "En attente",
  gagne: "Gagné",
  perdu: "Perdu",
};

export default function Premium() {
  const [coteCible, setCoteCible] = useState(3);
  const [nbTickets, setNbTickets] = useState(5);
  const [loading, setLoading] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);
  const [tickets, setTickets] = useState<TicketPremium[]>([]);

  async function charger() {
    try {
      setTickets(await listerPremium());
    } catch {
      /* ignore */
    }
  }

  useEffect(() => {
    charger();
  }, []);

  async function generer() {
    setLoading(true);
    setErreur(null);
    try {
      const r = await genererPremium(coteCible, nbTickets, 3);
      if (r.erreur) setErreur(r.erreur);
      else await charger(); // les nouveaux tickets sont persistés → on recharge
    } catch (e) {
      setErreur(e instanceof Error ? e.message : "Erreur réseau");
    } finally {
      setLoading(false);
    }
  }

  async function marquer(id: number, statut: "gagne" | "perdu" | "en_attente") {
    const t = await definirResultatPremium(id, statut);
    setTickets((arr) => arr.map((x) => (x.id === id ? t : x)));
  }

  async function supprimer(id: number) {
    await supprimerPremium(id);
    setTickets((arr) => arr.filter((x) => x.id !== id));
  }

  return (
    <>
      <div className="mb-xl flex items-center gap-sm">
        <Icon name="workspace_premium" className="text-tertiary" style={{ fontSize: 32 }} />
        <div>
          <h1 className="font-headline-lg text-headline-lg text-primary mb-xs">
            Tickets Premium
          </h1>
          <p className="font-body-lg text-on-surface-variant">
            Combinés à forte cote (3 · 5 · 10) construits par scan multi-matchs +
            consensus. Sauvegardés automatiquement.
          </p>
        </div>
      </div>

      {/* Contrôles */}
      <div className="glass-card rounded-xl p-lg mb-xl flex flex-col md:flex-row md:items-end gap-lg">
        <div>
          <label className="block font-label-md text-label-md text-on-surface-variant mb-sm">
            Cote cible
          </label>
          <div className="flex gap-sm">
            {COTES.map((c) => (
              <button
                key={c}
                onClick={() => setCoteCible(c)}
                className={`px-lg py-md rounded-lg font-mono font-bold transition-all ${
                  coteCible === c
                    ? "bg-primary text-on-primary"
                    : "bg-white/5 text-on-surface-variant hover:bg-white/10"
                }`}
              >
                {c.toFixed(2)}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="block font-label-md text-label-md text-on-surface-variant mb-sm">
            Nombre de tickets
          </label>
          <select
            value={nbTickets}
            onChange={(e) => setNbTickets(parseInt(e.target.value))}
            className="bg-surface-container-lowest border border-outline-variant text-on-surface rounded-lg px-md py-md font-label-md focus:ring-2 focus:ring-primary focus:outline-none"
          >
            {[3, 5, 10].map((n) => (
              <option key={n} value={n}>{n} tickets</option>
            ))}
          </select>
        </div>

        <button
          onClick={generer}
          disabled={loading}
          className="md:ml-auto flex items-center justify-center gap-sm bg-primary text-on-primary font-headline-sm text-headline-sm px-xl py-md rounded-xl hover:shadow-[0_0_25px_rgba(78,222,163,0.35)] transition-all active:scale-95 disabled:opacity-50 group"
        >
          {loading ? (
            <>
              <span className="w-5 h-5 border-2 border-on-primary border-t-transparent rounded-full animate-spin" />
              Scan en cours…
            </>
          ) : (
            <>
              <Icon name="bolt" className="group-hover:animate-pulse" />
              Générer (cote {coteCible})
            </>
          )}
        </button>
      </div>

      {erreur && (
        <div className="glass-card border-error/40 text-error p-lg rounded-xl mb-lg">
          Erreur : {erreur}
        </div>
      )}

      {tickets.length === 0 && !loading && (
        <div className="glass-card p-lg rounded-xl text-on-surface-variant text-center py-xl">
          <Icon name="workspace_premium" style={{ fontSize: 48 }} className="text-surface-container-highest" />
          <p className="mt-md">Aucun ticket premium encore. Choisis une cote et génère.</p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-lg">
        {tickets.map((t, i) => (
          <div
            key={t.id}
            className="glass-card p-lg rounded-xl flex flex-col card-enter"
            style={{ animationDelay: `${Math.min(i * 50, 500)}ms` }}
          >
            <div className="flex justify-between items-center mb-md">
              <span className="flex items-center gap-xs font-mono font-bold text-tertiary">
                <Icon name="workspace_premium" style={{ fontSize: 16 }} />
                Cible {t.cote_cible}
              </span>
              <span className={`px-sm py-xs rounded font-label-sm text-label-sm font-bold ${BADGE[t.statut]}`}>
                {LABEL[t.statut]}
              </span>
            </div>

            <div className="flex flex-col gap-sm mb-md flex-1">
              {t.selections.map((s, j) => (
                <div key={j} className="flex justify-between items-center p-sm rounded bg-white/5 border border-white/5">
                  <div className="flex flex-col">
                    <span className="font-body-sm text-body-sm text-on-surface">{s.match}</span>
                    <span className="font-label-sm text-label-sm text-secondary">🏆 {s.ligue} · {s.marche}</span>
                    {s.match_date && (
                      <span className="font-label-sm text-label-sm text-on-surface-variant/70">
                        {dateHeureCanada(s.match_date)}
                      </span>
                    )}
                  </div>
                  <span className="font-mono text-on-surface-variant">{s.cote.toFixed(2)}</span>
                </div>
              ))}
            </div>

            <div className="grid grid-cols-3 gap-sm pt-md border-t border-white/10 mb-md text-center">
              <div>
                <div className="font-label-sm text-label-sm text-on-surface-variant">Cote</div>
                <div className="font-mono font-bold text-primary text-headline-sm">{t.cote_totale.toFixed(2)}</div>
              </div>
              <div>
                <div className="font-label-sm text-label-sm text-on-surface-variant">Proba</div>
                <div className="font-mono font-bold text-secondary text-headline-sm">{Math.round(t.proba_reussite * 100)}%</div>
              </div>
              <div>
                <div className="font-label-sm text-label-sm text-on-surface-variant">Gain (10$)</div>
                <div className="font-mono font-bold text-tertiary text-headline-sm">{(t.cote_totale * 10).toFixed(0)}$</div>
              </div>
            </div>

            <div className="flex gap-sm">
              <button onClick={() => marquer(t.id, "gagne")} className="flex-1 bg-primary/15 hover:bg-primary hover:text-on-primary text-primary py-sm rounded-lg font-label-md text-label-md transition-all">Gagné</button>
              <button onClick={() => marquer(t.id, "perdu")} className="flex-1 bg-error/15 hover:bg-error hover:text-on-error text-error py-sm rounded-lg font-label-md text-label-md transition-all">Perdu</button>
              <button onClick={() => marquer(t.id, "en_attente")} title="Remettre en attente" className="px-sm bg-white/5 hover:bg-white/10 text-on-surface-variant rounded-lg transition-all"><Icon name="restart_alt" style={{ fontSize: 18 }} /></button>
              <button onClick={() => supprimer(t.id)} title="Supprimer" className="px-sm bg-white/5 hover:bg-error/20 text-on-surface-variant hover:text-error rounded-lg transition-all"><Icon name="delete" style={{ fontSize: 18 }} /></button>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
