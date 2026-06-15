"use client";

import { useEffect, useState } from "react";
import Icon from "../components/Icon";
import { EtudeML, getEtudeML } from "../lib/api";

const LIGUES = [
  { id: 39, nom: "Premier League" },
  { id: 140, nom: "La Liga" },
  { id: 135, nom: "Serie A" },
  { id: 78, nom: "Bundesliga" },
  { id: 61, nom: "Ligue 1" },
];

// Libellés lisibles des features du modèle
const FEAT_LABEL: Record<string, string> = {
  elo_diff: "Écart de force (Elo)",
  elo_home: "Force domicile (Elo)",
  elo_away: "Force extérieur (Elo)",
  xgf_h: "xG créé — domicile",
  xga_h: "xG concédé — domicile",
  xgf_a: "xG créé — extérieur",
  xga_a: "xG concédé — extérieur",
  xg_diff_h: "Différentiel xG domicile",
  xg_diff_a: "Différentiel xG extérieur",
  gf_h: "Buts marqués — domicile",
  ga_h: "Buts encaissés — domicile",
  gf_a: "Buts marqués — extérieur",
  ga_a: "Buts encaissés — extérieur",
};

export default function ModelePage() {
  const [league, setLeague] = useState(39);
  const [data, setData] = useState<EtudeML | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getEtudeML(league).then(setData).catch(() => setData(null)).finally(() => setLoading(false));
  }, [league]);

  const e = data?.etude;
  const gainLL = e ? e.elo.log_loss - e.ml.log_loss : 0; // > 0 = ML mieux calibré
  const maxImp = e && e.importance.length ? Math.max(...e.importance.map((i) => Math.abs(i.poids))) : 1;

  return (
    <>
      <div className="mb-lg">
        <h1 className="font-display-lg text-headline-lg font-black text-on-surface flex items-center gap-sm">
          <Icon name="smart_toy" className="text-primary" /> Étude du modèle
        </h1>
        <p className="text-sm text-on-surface-variant mt-xs max-w-2xl">
          Le 4e coéquipier : un modèle d&apos;apprentissage qui juge les équipes sur la qualité
          de leur jeu (xG) et pas seulement sur leurs résultats. Voici sa performance réelle,
          mesurée sur des matchs jamais vus à l&apos;entraînement.
        </p>
      </div>

      {/* Sélecteur de ligue */}
      <div className="flex gap-xs mb-xl overflow-x-auto pb-xs">
        {LIGUES.map((l) => (
          <button
            key={l.id}
            onClick={() => setLeague(l.id)}
            className={`px-md py-sm rounded-full text-xs font-semibold whitespace-nowrap transition-colors ${
              league === l.id ? "bg-primary text-on-primary" : "bg-surface-container-high text-on-surface-variant hover:bg-surface-container-highest"
            }`}
          >
            {l.nom}
          </button>
        ))}
      </div>

      {loading && (
        <div className="flex items-center justify-center py-xl">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {!loading && !e && (
        <div className="glass-card p-lg text-on-surface-variant text-sm">
          <p className="mb-sm">Modèle pas encore entraîné sur cette ligue, ou données insuffisantes.</p>
          <p className="text-on-surface-variant/60">Entraînement : <code className="text-primary">/api/ml/train?league={league}</code></p>
        </div>
      )}

      {!loading && e && (
        <div className="flex flex-col gap-xl">
          {/* Verdict global */}
          <div className="glass-card p-lg">
            <div className="flex items-center gap-sm mb-md">
              <Icon name={gainLL > 0 ? "verified" : "info"} className={gainLL > 0 ? "text-primary" : "text-tertiary"} />
              <span className="font-headline-sm text-headline-sm text-on-surface">
                {gainLL > 0
                  ? "Le modèle ML bat la référence Elo"
                  : "Le modèle ML est au niveau de l'Elo"}
              </span>
            </div>
            <p className="text-sm text-on-surface-variant">
              Entraîné sur <b className="text-on-surface">{e.n_train}</b> matchs, testé sur{" "}
              <b className="text-on-surface">{e.n_test}</b> matchs jamais vus. Mesure clé : le{" "}
              <b className="text-on-surface">log-loss</b> (plus bas = probabilités mieux calibrées).
            </p>
          </div>

          {/* Comparaison ML vs Elo */}
          <div>
            <p className="text-xs uppercase tracking-[0.15em] font-semibold text-on-surface-variant mb-md">
              Performance hors-échantillon
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-md">
              <CompareTile titre="Log-loss" sous="plus bas = mieux" ml={e.ml.log_loss} elo={e.elo.log_loss} mlMieux={e.ml.log_loss < e.elo.log_loss} />
              <CompareTile titre="Brier" sous="plus bas = mieux" ml={e.ml.brier_score} elo={e.elo.brier_score} mlMieux={e.ml.brier_score < e.elo.brier_score} />
              <CompareTile titre="Précision 1X2" sous="% de bons pronostics" ml={e.ml.accuracy_1x2} elo={e.elo.accuracy_1x2} suffixe="%" mlMieux={e.ml.accuracy_1x2 > e.elo.accuracy_1x2} />
            </div>
          </div>

          {/* Importance des features */}
          {e.importance.length > 0 && (
            <div>
              <p className="text-xs uppercase tracking-[0.15em] font-semibold text-on-surface-variant mb-xs">
                Ce qui compte pour le modèle
              </p>
              <p className="text-xs text-on-surface-variant/60 mb-md">
                Impact de chaque donnée sur la prédiction (plus la barre est longue, plus c&apos;est décisif).
              </p>
              <div className="glass-card p-lg flex flex-col gap-sm">
                {e.importance.filter((i) => i.poids > 0).slice(0, 8).map((i) => (
                  <div key={i.feature} className="flex items-center gap-md">
                    <span className="text-xs text-on-surface-variant w-44 flex-shrink-0 truncate">
                      {FEAT_LABEL[i.feature] ?? i.feature}
                    </span>
                    <div className="flex-1 h-3 bg-surface-container-highest rounded-full overflow-hidden">
                      <div className="h-full bg-primary rounded-full" style={{ width: `${(i.poids / maxImp) * 100}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Calibration */}
          {e.ml.calibration.length > 0 && (
            <div>
              <p className="text-xs uppercase tracking-[0.15em] font-semibold text-on-surface-variant mb-xs">
                Calibration
              </p>
              <p className="text-xs text-on-surface-variant/60 mb-md">
                Quand le modèle annonce X%, l&apos;issue arrive-t-elle vraiment X% du temps ? (idéal : barre ≈ marqueur)
              </p>
              <div className="glass-card p-lg flex flex-col gap-xs">
                {e.ml.calibration.map((c) => (
                  <div key={c.bin} className="flex items-center gap-sm">
                    <span className="text-xs text-on-surface-variant w-16 flex-shrink-0">{c.bin}</span>
                    <div className="flex-1 relative h-5 bg-surface-container-highest rounded overflow-hidden">
                      <div className="absolute inset-y-0 left-0 bg-primary/40" style={{ width: `${c.reussite_reelle}%` }} />
                      <div className="absolute inset-y-0 w-0.5 bg-secondary" style={{ left: `${c.proba_moyenne}%` }} />
                    </div>
                    <span className="text-xs font-mono text-on-surface w-24 flex-shrink-0 text-right">
                      {c.reussite_reelle}% <span className="text-on-surface-variant/50">({c.n})</span>
                    </span>
                  </div>
                ))}
                <div className="flex gap-md mt-sm text-xs text-on-surface-variant/60">
                  <span className="flex items-center gap-xs"><span className="w-3 h-2 bg-primary/40 rounded-sm inline-block" /> réussite réelle</span>
                  <span className="flex items-center gap-xs"><span className="w-0.5 h-3 bg-secondary inline-block" /> proba annoncée</span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </>
  );
}

function CompareTile({
  titre, sous, ml, elo, suffixe = "", mlMieux,
}: {
  titre: string; sous: string; ml: number; elo: number; suffixe?: string; mlMieux: boolean;
}) {
  return (
    <div className="glass-card glass-static p-md">
      <div className="text-[11px] uppercase tracking-wider text-on-surface-variant/70">{titre}</div>
      <div className="text-[10px] text-on-surface-variant/50 mb-sm">{sous}</div>
      <div className="flex items-end justify-between gap-sm">
        <div>
          <div className="text-[10px] text-on-surface-variant/60">ML (xG)</div>
          <div className={`font-mono font-black text-2xl ${mlMieux ? "text-primary" : "text-on-surface"}`}>
            {ml}{suffixe}
          </div>
        </div>
        <div className="text-right">
          <div className="text-[10px] text-on-surface-variant/60">Elo</div>
          <div className="font-mono font-bold text-lg text-on-surface-variant">{elo}{suffixe}</div>
        </div>
      </div>
    </div>
  );
}
