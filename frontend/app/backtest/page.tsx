"use client";

import { useState } from "react";
import Icon from "../components/Icon";
import { runBacktest, BacktestResult } from "../lib/api";
import { LIGUES } from "../lib/ligues";

const SAISONS = [2025, 2024, 2023, 2022, 2021, 2020];
const LIMITES = [
  { label: "20 derniers matchs", value: 20 },
  { label: "50 derniers matchs", value: 50 },
  { label: "Saison complète", value: 0 },
];

const LABEL_1X2: Record<string, string> = { "1": "Dom.", "X": "Nul", "2": "Ext." };

function AccuracyCard({
  label,
  pct,
  ok,
  total,
  color,
}: {
  label: string;
  pct: number;
  ok: number;
  total: number;
  color: string;
}) {
  const radius = 28;
  const circ = 2 * Math.PI * radius;
  const fill = (pct / 100) * circ;

  return (
    <div className="glass-card rounded-2xl p-lg flex flex-col items-center gap-sm">
      <svg width="80" height="80" viewBox="0 0 80 80">
        <circle cx="40" cy="40" r={radius} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="7" />
        <circle
          cx="40" cy="40" r={radius}
          fill="none"
          stroke={color}
          strokeWidth="7"
          strokeLinecap="round"
          strokeDasharray={`${fill} ${circ}`}
          transform="rotate(-90 40 40)"
          style={{ transition: "stroke-dasharray 0.6s ease" }}
        />
        <text x="40" y="44" textAnchor="middle" fill={color} fontSize="16" fontWeight="700" fontFamily="monospace">
          {pct}%
        </text>
      </svg>
      <p className="text-sm font-semibold text-on-surface">{label}</p>
      <p className="text-xs text-on-surface-variant">{ok} / {total} corrects</p>
    </div>
  );
}

export default function BacktestPage() {
  const [league, setLeague] = useState(39);
  const [season, setSeason] = useState(2024);
  const [limit, setLimit] = useState(0);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);

  async function lancer() {
    setLoading(true);
    setResult(null);
    setErreur(null);
    try {
      const r = await runBacktest(league, season, limit);
      setResult(r);
    } catch (e) {
      setErreur("Erreur lors du backtest. Vérifie que le backend est actif.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <div className="mb-xl">
        <h1 className="font-headline-lg text-headline-lg text-primary mb-xs flex items-center gap-sm">
          <Icon name="science" /> Backtest
        </h1>
        <p className="text-sm text-on-surface-variant">
          Rejoue le modèle Poisson sur les matchs terminés d&apos;une saison et mesure sa précision réelle.
        </p>
      </div>

      {/* Contrôles */}
      <div className="glass-card rounded-2xl p-lg mb-xl">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-md mb-lg">
          <div className="flex flex-col gap-xs">
            <label className="text-xs text-on-surface-variant font-medium uppercase tracking-wider">Ligue</label>
            <select
              value={league}
              onChange={(e) => setLeague(Number(e.target.value))}
              className="bg-surface-container-high text-on-surface rounded-xl px-md py-sm text-sm border border-white/10 focus:outline-none focus:border-primary/50"
            >
              {LIGUES.map((l) => (
                <option key={l.id} value={l.id}>{l.nom}</option>
              ))}
            </select>
          </div>

          <div className="flex flex-col gap-xs">
            <label className="text-xs text-on-surface-variant font-medium uppercase tracking-wider">Saison</label>
            <select
              value={season}
              onChange={(e) => setSeason(Number(e.target.value))}
              className="bg-surface-container-high text-on-surface rounded-xl px-md py-sm text-sm border border-white/10 focus:outline-none focus:border-primary/50"
            >
              {SAISONS.map((s) => (
                <option key={s} value={s}>{s}/{s + 1}</option>
              ))}
            </select>
          </div>

          <div className="flex flex-col gap-xs">
            <label className="text-xs text-on-surface-variant font-medium uppercase tracking-wider">Volume</label>
            <select
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
              className="bg-surface-container-high text-on-surface rounded-xl px-md py-sm text-sm border border-white/10 focus:outline-none focus:border-primary/50"
            >
              {LIMITES.map((l) => (
                <option key={l.value} value={l.value}>{l.label}</option>
              ))}
            </select>
          </div>
        </div>

        <button
          onClick={lancer}
          disabled={loading}
          className="flex items-center gap-sm bg-primary text-on-primary font-semibold px-lg py-sm rounded-xl hover:shadow-[0_0_20px_rgba(78,222,163,0.3)] transition-all active:scale-95 disabled:opacity-50"
        >
          <Icon name={loading ? "hourglass_top" : "play_arrow"} style={{ fontSize: 18 }} />
          {loading ? "Calcul en cours…" : "Lancer le backtest"}
        </button>

        {loading && (
          <p className="text-xs text-on-surface-variant mt-sm">
            Première exécution : ~20 appels API (mis en cache ensuite).
          </p>
        )}

        {erreur && <p className="text-error text-sm mt-sm">{erreur}</p>}
      </div>

      {/* Résultats */}
      {result && (
        <>
          <div className="flex items-center justify-between mb-lg">
            <h2 className="text-lg font-bold text-on-surface">
              {result.ligue} — {result.saison}/{result.saison + 1}
            </h2>
            <span className="text-xs text-on-surface-variant bg-surface-container-high px-sm py-xs rounded-full">
              {result.total_matches} matchs analysés
            </span>
          </div>

          {/* Métriques */}
          <div className="flex flex-col gap-lg mb-xl">

            {/* Résultat du match */}
            <div>
              <p className="text-xs text-on-surface-variant uppercase tracking-wider mb-sm font-medium">Résultat du match (1X2)</p>
              <div className="grid grid-cols-1 gap-md">
                <AccuracyCard label="Prédiction correcte" pct={result.accuracy_1x2} ok={result.ok_1x2} total={result.total_matches} color="#4edea3" />
              </div>
            </div>

            {/* +/- 2.5 buts */}
            <div>
              <p className="text-xs text-on-surface-variant uppercase tracking-wider mb-sm font-medium">Plus / Moins de 2.5 buts</p>
              <div className="grid grid-cols-2 gap-md">
                <AccuracyCard label="Quand modèle prédit Plus" pct={result.accuracy_over25} ok={result.ok_over25} total={result.n_over25} color="#adc6ff" />
                <AccuracyCard label="Quand modèle prédit Moins" pct={result.accuracy_under25} ok={result.ok_under25} total={result.n_under25} color="#adc6ff" />
              </div>
            </div>

            {/* +/- 1.5 buts */}
            <div>
              <p className="text-xs text-on-surface-variant uppercase tracking-wider mb-sm font-medium">Plus / Moins de 1.5 buts</p>
              <div className="grid grid-cols-2 gap-md">
                <AccuracyCard label="Quand modèle prédit Plus" pct={result.accuracy_over15} ok={result.ok_over15} total={result.n_over15} color="#adc6ff" />
                <AccuracyCard label="Quand modèle prédit Moins" pct={result.accuracy_under15} ok={result.ok_under15} total={result.n_under15} color="#adc6ff" />
              </div>
            </div>

            {/* Les 2 équipes marquent */}
            <div>
              <p className="text-xs text-on-surface-variant uppercase tracking-wider mb-sm font-medium">Les 2 équipes marquent</p>
              <div className="grid grid-cols-2 gap-md">
                <AccuracyCard label="Quand modèle prédit Oui" pct={result.accuracy_btts_oui} ok={result.ok_btts_oui} total={result.n_btts_oui} color="#ffb95f" />
                <AccuracyCard label="Quand modèle prédit Non" pct={result.accuracy_btts_non} ok={result.ok_btts_non} total={result.n_btts_non} color="#ffb95f" />
              </div>
            </div>

            {/* Double chance */}
            <div>
              <p className="text-xs text-on-surface-variant uppercase tracking-wider mb-sm font-medium">Double chance</p>
              <div className="grid grid-cols-2 gap-md">
                <AccuracyCard label="Pas de match nul" pct={result.accuracy_dc_12} ok={result.ok_dc_12} total={result.n_dc_12} color="#c084fc" />
                <AccuracyCard label="Domicile ne perd pas" pct={result.accuracy_dc_1x} ok={result.ok_dc_1x} total={result.n_dc_1x} color="#c084fc" />
              </div>
            </div>
          </div>

          {/* Table des matchs */}
          <div className="glass-card rounded-2xl overflow-hidden">
            <div className="px-lg py-md border-b border-white/8">
              <h3 className="text-sm font-semibold text-on-surface">Détail match par match</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-xs text-on-surface-variant" style={{ borderBottom: "1px solid rgba(255,255,255,0.07)" }}>
                    <th className="text-left px-lg py-sm font-medium">Match</th>
                    <th className="text-center px-sm py-sm font-medium">Score</th>
                    <th className="text-center px-sm py-sm font-medium">Résultat</th>
                    <th className="text-center px-sm py-sm font-medium">+/- 2.5 buts</th>
                    <th className="text-center px-sm py-sm font-medium">+/- 1.5 buts</th>
                    <th className="text-center px-sm py-sm font-medium">2 équipes marquent</th>
                    <th className="text-center px-sm py-sm font-medium">Pas de nul</th>
                    <th className="text-center px-sm py-sm font-medium">Dom. ne perd pas</th>
                  </tr>
                </thead>
                <tbody>
                  {[...result.matchs].reverse().map((m) => (
                    <tr
                      key={m.fixture_id}
                      style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}
                      className="hover:bg-white/3 transition-colors"
                    >
                      <td className="px-lg py-sm">
                        <span className="text-on-surface font-medium">{m.match}</span>
                      </td>
                      <td className="px-sm py-sm text-center">
                        <span className="font-mono font-bold text-on-surface">{m.score}</span>
                      </td>
                      <td className="px-sm py-sm text-center">
                        <span className={`inline-flex items-center gap-1 text-xs font-medium px-sm py-xs rounded-full ${m.bon_1x2 ? "bg-primary/15 text-primary" : "bg-error/15 text-error"}`}>
                          {m.bon_1x2 ? "✓" : "✗"} {LABEL_1X2[m.pred_1x2]} → {LABEL_1X2[m.reel_1x2]}
                        </span>
                      </td>
                      <td className="px-sm py-sm text-center">
                        <span className={`inline-flex items-center gap-1 text-xs font-medium px-sm py-xs rounded-full ${m.bon_over25 ? "bg-primary/15 text-primary" : "bg-error/15 text-error"}`}>
                          {m.bon_over25 ? "✓" : "✗"} {m.pred_over25 === "over_2.5" ? "+2.5" : "-2.5"}
                        </span>
                      </td>
                      <td className="px-sm py-sm text-center">
                        <span className={`inline-flex items-center gap-1 text-xs font-medium px-sm py-xs rounded-full ${m.bon_over15 ? "bg-primary/15 text-primary" : "bg-error/15 text-error"}`}>
                          {m.bon_over15 ? "✓" : "✗"} {m.pred_over15 === "over_1.5" ? "+1.5" : "-1.5"}
                        </span>
                      </td>
                      <td className="px-sm py-sm text-center">
                        <span className={`inline-flex items-center gap-1 text-xs font-medium px-sm py-xs rounded-full ${m.bon_btts ? "bg-primary/15 text-primary" : "bg-error/15 text-error"}`}>
                          {m.bon_btts ? "✓" : "✗"} {m.pred_btts === "btts_oui" ? "Oui" : "Non"}
                        </span>
                      </td>
                      <td className="px-sm py-sm text-center">
                        <span className={`inline-flex items-center gap-1 text-xs font-medium px-sm py-xs rounded-full ${m.bon_dc_12 ? "bg-primary/15 text-primary" : "bg-error/15 text-error"}`}>
                          {m.bon_dc_12 ? "✓" : "✗"} {m.pred_dc_12 === "12" ? "Oui" : "Non"}
                        </span>
                      </td>
                      <td className="px-sm py-sm text-center">
                        <span className={`inline-flex items-center gap-1 text-xs font-medium px-sm py-xs rounded-full ${m.bon_dc_1x ? "bg-primary/15 text-primary" : "bg-error/15 text-error"}`}>
                          {m.bon_dc_1x ? "✓" : "✗"} {m.pred_dc_1x === "1X" ? "Oui" : "Non"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </>
  );
}
