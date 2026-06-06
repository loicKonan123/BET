"use client";

import { useEffect, useState } from "react";
import AnalyseMatch from "../components/AnalyseMatch";
import Icon from "../components/Icon";
import { Analyse, getAnalyses } from "../lib/api";

export default function Analyses() {
  const [analyses, setAnalyses] = useState<Analyse[]>([]);
  const [loading, setLoading] = useState(true);
  const [erreur, setErreur] = useState<string | null>(null);
  const [filtre, setFiltre] = useState<string>("Toutes");

  useEffect(() => {
    getAnalyses()
      .then((d) => {
        if (d.erreur) setErreur(d.erreur);
        else setAnalyses(d.analyses);
      })
      .catch((e) => setErreur(e instanceof Error ? e.message : "Erreur réseau"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <>
      <div className="mb-xl max-w-4xl">
        <h1 className="font-headline-lg text-headline-lg text-primary mb-xs">
          Analyses des matchs
        </h1>
        <p className="font-body-lg text-on-surface-variant">
          Tous les matchs jouables sur Mise-o-jeu. Clique sur un match pour
          l&apos;analyse détaillée et notre conseil de paris.
        </p>
      </div>

      {loading && (
        <div className="flex flex-col items-center justify-center py-xl">
          <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin mb-md" />
          <p className="text-primary font-label-md animate-pulse">
            SCAN DES MATCHS EN COURS…
          </p>
        </div>
      )}

      {erreur && (
        <div className="glass-card border-error/40 text-error p-lg rounded-xl">
          Erreur : {erreur}
        </div>
      )}

      {!loading && !erreur && analyses.length === 0 && (
        <div className="glass-card p-lg rounded-xl text-on-surface-variant text-center py-xl">
          <Icon name="search_off" style={{ fontSize: 48 }} className="text-surface-container-highest" />
          <p className="mt-md">Aucun match jouable trouvé dans la fenêtre actuelle.</p>
        </div>
      )}

      {/* Filtre par compétition */}
      {analyses.length > 0 &&
        (() => {
          const compteur = analyses.reduce<Record<string, number>>((acc, a) => {
            acc[a.ligue] = (acc[a.ligue] ?? 0) + 1;
            return acc;
          }, {});
          const ligues = Object.keys(compteur).sort();
          const onglets = [
            { nom: "Toutes", n: analyses.length },
            ...ligues.map((l) => ({ nom: l, n: compteur[l] })),
          ];
          return (
            <div className="flex flex-wrap gap-sm mb-lg">
              {onglets.map((o) => {
                const actif = filtre === o.nom;
                return (
                  <button
                    key={o.nom}
                    onClick={() => setFiltre(o.nom)}
                    className={`px-md py-xs rounded-full font-label-sm text-label-sm transition-all border ${
                      actif
                        ? "bg-secondary-container text-on-secondary-container border-transparent"
                        : "bg-white/5 text-on-surface-variant border-white/10 hover:border-primary/30"
                    }`}
                  >
                    {o.nom} <span className="opacity-60">({o.n})</span>
                  </button>
                );
              })}
            </div>
          );
        })()}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-lg">
        {analyses
          .filter((a) => filtre === "Toutes" || a.ligue === filtre)
          .map((a) => (
            <AnalyseMatch key={a.fixture_id} a={a} href={`/match/${a.fixture_id}`} />
          ))}
      </div>
    </>
  );
}
