"use client";

import Link from "next/link";
import { useState } from "react";
import Icon from "../components/Icon";
import { Combine, Resultat, genererTickets, sauverTicket } from "../lib/api";

export default function Generate() {
  const [nb, setNb] = useState(5);
  const [loading, setLoading] = useState(false);
  const [res, setRes] = useState<Resultat | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [saved, setSaved] = useState<Record<number, boolean>>({});

  async function generer() {
    setLoading(true);
    setErreur(null);
    setRes(null);
    setSaved({});
    try {
      const data = await genererTickets(nb);
      if (data.erreur) setErreur(data.erreur);
      else setRes(data);
    } catch (e: unknown) {
      setErreur(e instanceof Error ? e.message : "Erreur réseau");
    } finally {
      setLoading(false);
    }
  }

  async function sauver(c: Combine, i: number) {
    try {
      await sauverTicket(c);
      setSaved((s) => ({ ...s, [i]: true }));
    } catch {
      setErreur("Impossible de sauvegarder le ticket.");
    }
  }

  return (
    <>
      {/* En-tête */}
      <div className="mb-xl max-w-4xl">
        <h1 className="font-headline-lg text-headline-lg text-primary mb-xs">
          Générer des tickets
        </h1>
        <p className="font-body-lg text-on-surface-variant">
          Scan automatique des matchs — tickets bâtis sur les issues
          les plus probables du consensus (Poisson ajusté + Elo + marché).
        </p>
      </div>

      {/* Contrôles */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-lg mb-xl">
        <div className="lg:col-span-8 glass-card p-lg rounded-xl flex flex-col md:flex-row items-center justify-between gap-lg">
          <div className="w-full md:w-auto">
            <label className="block font-label-md text-label-md text-on-surface-variant mb-xs ml-1">
              Nombre de tickets
            </label>
            <select
              value={nb}
              onChange={(e) => setNb(parseInt(e.target.value))}
              className="w-full md:w-48 bg-surface-container-lowest border border-outline-variant text-on-surface rounded-lg px-md py-md font-label-md focus:ring-2 focus:ring-primary focus:outline-none appearance-none cursor-pointer"
            >
              <option value={3}>3 Tickets</option>
              <option value={5}>5 Tickets</option>
              <option value={10}>10 Tickets</option>
            </select>
          </div>
          <button
            onClick={generer}
            disabled={loading}
            className="w-full md:w-auto flex items-center justify-center gap-sm bg-primary text-on-primary font-headline-sm text-headline-sm px-xl py-md rounded-xl hover:shadow-[0_0_20px_rgba(78,222,163,0.3)] transition-all active:scale-95 disabled:opacity-50 group"
          >
            <Icon name="bolt" className="group-hover:animate-pulse" />
            {loading ? "Analyse…" : "Générer les tickets"}
          </button>
        </div>

        {/* Statut moteur */}
        <div className="lg:col-span-4 glass-card p-lg rounded-xl flex flex-col justify-center">
          <span className="font-label-sm text-label-sm uppercase tracking-widest text-on-surface-variant mb-sm">
            Statut du moteur
          </span>
          <div className="flex items-center gap-sm">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-primary"></span>
            </span>
            <span className="font-label-md text-label-md text-on-surface font-bold">
              {res
                ? `${res.nb_matchs_analyses} MATCHS · ${res.nb_combines} TICKETS`
                : "CONSENSUS_V2 READY"}
            </span>
          </div>
        </div>
      </section>

      {erreur && (
        <div className="glass-card border-error/40 text-error p-lg rounded-xl mb-lg">
          Erreur : {erreur}
        </div>
      )}

      {loading && (
        <div className="flex flex-col items-center justify-center py-xl">
          <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin mb-md"></div>
          <p className="text-primary font-label-md animate-pulse">
            CALCUL DES PROBABILITÉS…
          </p>
        </div>
      )}

      {!loading && !res && !erreur && (
        <div className="py-xl text-center">
          <Icon
            name="confirmation_number"
            className="text-surface-container-highest"
            style={{ fontSize: 64 }}
          />
          <p className="text-on-surface-variant font-body-lg mt-md">
            Appuyez sur le bouton pour générer vos tickets.
          </p>
        </div>
      )}

      {res && res.combines.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-lg mb-xl">
          {res.combines.map((c, i) => (
            <div key={i} className="glass-card p-lg rounded-xl relative overflow-hidden">
              <div className="absolute top-0 right-0 p-md opacity-10 pointer-events-none">
                <Icon name="verified" style={{ fontSize: 80 }} />
              </div>

              <div className="flex justify-between items-start mb-md">
                <div className="flex flex-col">
                  <span className="font-label-sm text-label-sm text-on-surface-variant">TICKET</span>
                  <span className="font-label-md text-label-md font-bold text-primary">
                    #{String(i + 1).padStart(2, "0")}
                  </span>
                </div>
                <div className="flex flex-col items-end">
                  <span className="font-label-sm text-label-sm text-on-surface-variant">CONFIANCE</span>
                  <div className="flex items-center gap-xs">
                    <div className="h-1 w-16 bg-surface-container-highest rounded-full overflow-hidden">
                      <div className="h-full bg-primary" style={{ width: `${c.proba_reussite * 100}%` }} />
                    </div>
                    <span className="font-label-sm text-label-sm text-primary">
                      {Math.round(c.proba_reussite * 100)}%
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex flex-col gap-sm mb-lg">
                {c.selections.map((s, j) => {
                  const contenu = (
                    <>
                      <div className="flex flex-col min-w-0">
                        <span className="font-body-sm text-body-sm text-on-surface truncate">{s.match}</span>
                        <span className="font-label-sm text-label-sm text-secondary truncate">🏆 {s.ligue} · {s.marche}</span>
                      </div>
                      <div className="flex items-center gap-sm flex-shrink-0">
                        <span className="font-label-sm text-label-sm text-primary">{Math.round(s.proba * 100)}%</span>
                        <span className="font-label-md text-label-md text-on-surface-variant">{s.cote.toFixed(2)}</span>
                        {s.fixture_id && <Icon name="chevron_right" className="text-on-surface-variant/40" style={{ fontSize: 16 }} />}
                      </div>
                    </>
                  );
                  return s.fixture_id ? (
                    <Link
                      key={j}
                      href={`/match/${s.fixture_id}`}
                      className="flex items-center justify-between gap-sm p-sm rounded bg-white/5 border border-white/5 hover:border-primary/40 hover:bg-white/10 transition-all group"
                    >
                      {contenu}
                    </Link>
                  ) : (
                    <div key={j} className="flex items-center justify-between gap-sm p-sm rounded bg-white/5 border border-white/5">
                      {contenu}
                    </div>
                  );
                })}
              </div>

              <div className="grid grid-cols-3 gap-sm pt-md border-t border-white/10">
                <Stat label="Cote" value={c.cote_totale.toFixed(2)} color="primary" />
                <Stat label="Proba" value={`${Math.round(c.proba_reussite * 100)}%`} color="secondary" />
                <Stat label="Value" value={`${c.value >= 0 ? "+" : ""}${Math.round(c.value * 100)}%`} color="tertiary" />
              </div>

              <button
                onClick={() => sauver(c, i)}
                disabled={saved[i]}
                className="mt-lg w-full bg-white/10 hover:bg-primary hover:text-on-primary border border-white/10 hover:border-primary transition-all py-sm rounded-lg font-label-md text-label-md flex items-center justify-center gap-sm group disabled:opacity-60 disabled:hover:bg-white/10 disabled:hover:text-on-surface"
              >
                {saved[i] ? "✔ Enregistré" : "Sauvegarder dans l'historique"}
                {!saved[i] && (
                  <Icon name="bookmark_add" className="transition-transform group-hover:translate-x-1" style={{ fontSize: 18 }} />
                )}
              </button>
            </div>
          ))}
        </div>
      )}

      {res && res.combines.length === 0 && (
        <div className="glass-card p-lg rounded-xl text-on-surface-variant">
          Aucun ticket pour le moment — aucun match disponible dans la
          fenêtre, ou cotes/stats indisponibles.
        </div>
      )}

      {res && res.analyses.length > 0 && (
        <Link
          href="/analyses"
          className="glass-card rounded-xl p-lg flex items-center justify-between hover:border-primary/30 transition-colors"
        >
          <span className="flex items-center gap-sm font-label-md text-label-md text-on-surface">
            <Icon name="insights" className="text-tertiary" />
            Voir l&apos;analyse détaillée des {res.analyses.length} matchs
          </span>
          <Icon name="arrow_forward" className="text-primary" />
        </Link>
      )}
    </>
  );
}

function Stat({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color: "primary" | "secondary" | "tertiary";
}) {
  const cls = {
    primary: "bg-primary/20 text-primary",
    secondary: "bg-secondary/20 text-secondary",
    tertiary: "bg-tertiary/20 text-tertiary",
  }[color];
  return (
    <div className="flex flex-col items-center">
      <span className="font-label-sm text-label-sm text-on-surface-variant mb-xs">{label}</span>
      <span className={`${cls} px-sm py-xs rounded font-label-md text-label-md font-bold w-full text-center`}>
        {value}
      </span>
    </div>
  );
}
