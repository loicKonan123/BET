"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import Icon from "../components/Icon";
import { sauverTicket } from "../lib/api";
import { useTicketBuilder } from "../lib/useTicketBuilder";

export default function TicketBuilderPage() {
  const router = useRouter();
  const { picks, remove, clear, coteTotale, probaReussite } = useTicketBuilder();
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  async function sauver() {
    if (picks.length === 0) return;
    setSaving(true);
    setErreur(null);
    try {
      await sauverTicket({
        cote_totale: coteTotale,
        proba_reussite: probaReussite,
        value: probaReussite * coteTotale - 1,
        selections: picks,
      });
      setSaved(true);
      clear();
    } catch {
      setErreur("Impossible de sauvegarder le ticket.");
    } finally {
      setSaving(false);
    }
  }

  if (saved) {
    return (
      <div className="flex flex-col items-center justify-center py-xl gap-lg">
        <div className="w-16 h-16 rounded-full bg-primary/20 flex items-center justify-center">
          <Icon name="check_circle" className="text-primary" style={{ fontSize: 40 }} />
        </div>
        <h1 className="font-headline-lg text-headline-lg text-primary">Ticket sauvegardé !</h1>
        <div className="flex gap-md">
          <button onClick={() => router.push("/history")} className="flex items-center gap-sm bg-primary text-on-primary px-lg py-sm rounded-xl font-label-md">
            <Icon name="history" style={{ fontSize: 18 }} /> Voir l&apos;historique
          </button>
          <button onClick={() => { setSaved(false); router.push("/analyses"); }} className="flex items-center gap-sm bg-white/10 text-on-surface px-lg py-sm rounded-xl font-label-md">
            <Icon name="insights" style={{ fontSize: 18 }} /> Continuer les analyses
          </button>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="mb-xl">
        <h1 className="font-headline-lg text-headline-lg text-primary mb-xs flex items-center gap-sm">
          <Icon name="receipt_long" /> Mon ticket
        </h1>
        <p className="font-body-lg text-on-surface-variant">
          Sélections ajoutées depuis les analyses.
        </p>
      </div>

      {picks.length === 0 ? (
        <div className="glass-card p-xl rounded-xl text-center">
          <Icon name="add_circle" className="text-surface-container-highest" style={{ fontSize: 56 }} />
          <p className="mt-md text-on-surface-variant font-body-lg">
            Aucune sélection pour l&apos;instant.
          </p>
          <button onClick={() => router.push("/analyses")} className="mt-lg inline-flex items-center gap-sm bg-secondary-container text-on-secondary-container px-lg py-sm rounded-xl font-label-md">
            <Icon name="insights" style={{ fontSize: 18 }} /> Parcourir les analyses
          </button>
        </div>
      ) : (
        <>
          <div className="flex flex-col gap-sm mb-lg">
            {picks.map((p, i) => (
              <div key={i} className="glass-card p-md rounded-xl flex items-center gap-md">
                <div className="flex flex-col flex-1 min-w-0">
                  <span className="font-body-md text-body-md text-on-surface font-semibold truncate">{p.match}</span>
                  <span className="font-label-sm text-label-sm text-secondary">🏆 {p.ligue} · {p.marche}</span>
                </div>
                <div className="flex items-center gap-md flex-shrink-0">
                  <div className="flex flex-col items-end">
                    <span className="font-mono font-bold text-primary">{p.cote.toFixed(2)}</span>
                    <span className="font-label-sm text-label-sm text-on-surface-variant">{Math.round(p.proba * 100)}%</span>
                  </div>
                  <button
                    onClick={() => remove(p.fixture_id, p.cle)}
                    className="w-8 h-8 rounded-lg bg-white/5 hover:bg-error/20 text-on-surface-variant hover:text-error transition-all flex items-center justify-center"
                  >
                    <Icon name="close" style={{ fontSize: 16 }} />
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Récap */}
          <div className="glass-card p-lg rounded-xl mb-lg border-primary/20" style={{ boxShadow: "0 0 20px rgba(78,222,163,0.08)" }}>
            <div className="grid grid-cols-3 gap-sm mb-lg">
              <div className="flex flex-col items-center bg-primary/10 rounded-lg p-md">
                <span className="font-label-sm text-label-sm text-on-surface-variant mb-xs">Cote totale</span>
                <span className="font-mono font-bold text-headline-md text-primary">{coteTotale.toFixed(2)}</span>
              </div>
              <div className="flex flex-col items-center bg-secondary/10 rounded-lg p-md">
                <span className="font-label-sm text-label-sm text-on-surface-variant mb-xs">Proba</span>
                <span className="font-mono font-bold text-headline-md text-secondary">{Math.round(probaReussite * 100)}%</span>
              </div>
              <div className="flex flex-col items-center bg-tertiary/10 rounded-lg p-md">
                <span className="font-label-sm text-label-sm text-on-surface-variant mb-xs">Sélections</span>
                <span className="font-mono font-bold text-headline-md text-tertiary">{picks.length}</span>
              </div>
            </div>

            {erreur && <p className="text-error font-label-md mb-md">{erreur}</p>}

            <div className="flex gap-sm">
              <button
                onClick={sauver}
                disabled={saving}
                className="flex-1 flex items-center justify-center gap-sm bg-primary text-on-primary font-headline-sm px-lg py-md rounded-xl hover:shadow-[0_0_20px_rgba(78,222,163,0.3)] transition-all active:scale-95 disabled:opacity-50"
              >
                <Icon name="bookmark_add" style={{ fontSize: 20 }} />
                {saving ? "Sauvegarde…" : "Sauvegarder le ticket"}
              </button>
              <button
                onClick={clear}
                className="px-lg py-md bg-white/5 hover:bg-error/10 text-on-surface-variant hover:text-error rounded-xl transition-all font-label-md"
              >
                Tout effacer
              </button>
            </div>
          </div>
        </>
      )}
    </>
  );
}
