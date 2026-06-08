"use client";

import { useEffect, useState } from "react";
import Icon from "../components/Icon";
import {
  TicketEnregistre,
  listerTickets,
  supprimerTicket,
  settlerTickets,
} from "../lib/api";
import { dateCanada } from "../lib/date";

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

export default function History() {
  const [tickets, setTickets] = useState<TicketEnregistre[]>([]);
  const [loading, setLoading] = useState(true);

  async function charger() {
    setLoading(true);
    try {
      setTickets(await listerTickets());
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    settlerTickets().catch(() => {}).finally(() => charger());
  }, []);

  async function supprimer(id: number) {
    await supprimerTicket(id);
    setTickets((arr) => arr.filter((x) => x.id !== id));
  }

  return (
    <>
      <div className="mb-xl">
        <h1 className="font-headline-lg text-headline-lg text-primary mb-xs">
          Historique des tickets
        </h1>
        <p className="font-body-lg text-on-surface-variant">
          Résultats vérifiés automatiquement dès que les matchs sont terminés.
        </p>
      </div>

      {loading && (
        <div className="flex justify-center py-xl">
          <div className="w-10 h-10 border-4 border-primary border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {!loading && tickets.length === 0 && (
        <div className="glass-card p-lg rounded-xl text-on-surface-variant text-center py-xl">
          <Icon name="inbox" style={{ fontSize: 48 }} className="text-surface-container-highest" />
          <p className="mt-md">Aucun ticket sauvegardé. Génère et sauvegarde des tickets depuis l&apos;onglet Ticket Gen.</p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-lg">
        {tickets.map((t) => (
          <div key={t.id} className="glass-card p-lg rounded-xl flex flex-col">
            <div className="flex justify-between items-center mb-md">
              <div className="flex flex-col">
                <span className="font-label-sm text-label-sm text-on-surface-variant">
                  TICKET #{String(t.id).padStart(2, "0")}
                </span>
                <span className="font-label-sm text-label-sm text-on-surface-variant">
                  {dateCanada(t.cree_le)}
                </span>
              </div>
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
                  </div>
                  <span className="font-label-md text-label-md text-on-surface-variant">{s.cote.toFixed(2)}</span>
                </div>
              ))}
            </div>

            <div className="flex justify-between items-center text-label-md font-label-md mb-md pt-md border-t border-white/10">
              <span className="text-primary font-bold">Cote {t.cote_totale.toFixed(2)}</span>
              <span className="text-secondary">Proba {Math.round(t.proba_reussite * 100)}%</span>
            </div>

            <div className="flex justify-end">
              <button
                onClick={() => supprimer(t.id)}
                title="Supprimer"
                className="px-sm py-sm bg-white/5 hover:bg-error/20 text-on-surface-variant hover:text-error rounded-lg transition-all"
              >
                <Icon name="delete" style={{ fontSize: 18 }} />
              </button>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
