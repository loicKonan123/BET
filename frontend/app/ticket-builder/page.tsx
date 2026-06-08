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
        <div className="glass-card p-8 rounded-2xl text-center max-w-120 mx-auto">
          <Icon name="add_circle" className="text-surface-container-highest" style={{ fontSize: 56 }} />
          <p className="mt-md text-on-surface-variant font-body-lg">
            Aucune sélection pour l&apos;instant.
          </p>
          <button onClick={() => router.push("/analyses")} className="mt-lg inline-flex items-center gap-sm bg-secondary-container text-on-secondary-container px-lg py-sm rounded-xl font-label-md">
            <Icon name="insights" style={{ fontSize: 18 }} /> Parcourir les analyses
          </button>
        </div>
      ) : (
        <div className="max-w-[560px] mx-auto">
          <div className="glass-card rounded-2xl overflow-hidden mb-lg">

            {/* Sélections */}
            {picks.map((p, i) => (
              <div
                key={i}
                className="flex items-center gap-md px-lg py-md"
                style={{ borderBottom: "1px solid rgba(255,255,255,0.07)" }}
              >
                <div className="flex flex-col flex-1 min-w-0">
                  <span className="text-sm font-semibold text-on-surface truncate">{p.match}</span>
                  <span className="text-xs text-on-surface-variant mt-1">
                    {p.ligue} · <span className="text-secondary font-medium">{p.marche}</span>
                  </span>
                </div>
                <div className="flex items-center gap-md shrink-0">
                  <div className="flex flex-col items-end">
                    <span className="font-mono font-bold text-primary text-base leading-none">{p.cote.toFixed(2)}</span>
                    <span className="text-xs text-on-surface-variant mt-1">{Math.round(p.proba * 100)}%</span>
                  </div>
                  <button
                    onClick={() => remove(p.fixture_id, p.cle)}
                    className="w-7 h-7 rounded-lg hover:bg-error/20 text-on-surface-variant hover:text-error transition-all flex items-center justify-center"
                  >
                    <Icon name="close" style={{ fontSize: 14 }} />
                  </button>
                </div>
              </div>
            ))}

            {/* Séparateur */}
            <div
              className="mx-lg my-sm"
              style={{ borderTop: "1px dashed rgba(255,255,255,0.15)" }}
            />

            {/* Récap */}
            <div className="px-lg pb-lg">
              <div className="grid grid-cols-3 gap-sm mb-lg">
                <div className="flex flex-col items-center rounded-xl p-md" style={{ background: "rgba(78,222,163,0.08)" }}>
                  <span className="text-xs text-on-surface-variant mb-1">Cote totale</span>
                  <span className="font-mono font-bold text-2xl text-primary">{coteTotale.toFixed(2)}</span>
                </div>
                <div className="flex flex-col items-center rounded-xl p-md" style={{ background: "rgba(173,198,255,0.08)" }}>
                  <span className="text-xs text-on-surface-variant mb-1">Proba</span>
                  <span className="font-mono font-bold text-2xl text-secondary">{Math.round(probaReussite * 100)}%</span>
                </div>
                <div className="flex flex-col items-center rounded-xl p-md" style={{ background: "rgba(255,185,95,0.08)" }}>
                  <span className="text-xs text-on-surface-variant mb-1">Sélections</span>
                  <span className="font-mono font-bold text-2xl text-tertiary">{picks.length}</span>
                </div>
              </div>

              {erreur && <p className="text-error text-sm mb-md">{erreur}</p>}

              <div className="flex gap-sm">
                <button
                  onClick={sauver}
                  disabled={saving}
                  className="flex-1 flex items-center justify-center gap-sm bg-primary text-on-primary font-semibold px-lg py-md rounded-xl hover:shadow-[0_0_20px_rgba(78,222,163,0.3)] transition-all active:scale-95 disabled:opacity-50"
                >
                  <Icon name="bookmark_add" style={{ fontSize: 20 }} />
                  {saving ? "Sauvegarde…" : "Sauvegarder le ticket"}
                </button>
                <button
                  onClick={clear}
                  className="px-lg py-md hover:bg-error/10 text-on-surface-variant hover:text-error rounded-xl transition-all text-sm"
                  style={{ background: "rgba(255,255,255,0.05)" }}
                >
                  Tout effacer
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
