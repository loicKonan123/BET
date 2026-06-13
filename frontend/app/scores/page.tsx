"use client";

import Link from "next/link";
import { useEffect, useState, useCallback } from "react";
import Icon from "../components/Icon";
import { ScoreMatch, ScoresJour, getScores } from "../lib/api";
import { dateHeureCanada } from "../lib/date";

const LIVE_ST  = new Set(["1H", "2H", "HT", "ET", "BT", "P", "INT"]);
const DONE_ST  = new Set(["FT", "AET", "PEN", "AWD", "WO"]);

function dateISO(d: Date) {
  return d.toISOString().slice(0, 10);
}

function addDays(iso: string, n: number) {
  const d = new Date(iso + "T12:00:00Z");
  d.setUTCDate(d.getUTCDate() + n);
  return dateISO(d);
}

function labelDate(iso: string) {
  const today = dateISO(new Date());
  const hier  = addDays(today, -1);
  const dem   = addDays(today, 1);
  if (iso === today) return "Aujourd'hui";
  if (iso === hier)  return "Hier";
  if (iso === dem)   return "Demain";
  const d = new Date(iso + "T12:00:00Z");
  return d.toLocaleDateString("fr-CA", { weekday: "short", day: "numeric", month: "short" });
}

function StatusBadge({ status, elapsed }: { status: string; elapsed: number | null }) {
  if (LIVE_ST.has(status)) {
    return (
      <span className="flex items-center gap-[3px]">
        <span className="w-[6px] h-[6px] rounded-full bg-red-500 animate-pulse flex-shrink-0" />
        <span className="text-[10px] font-bold text-red-400">
          {status === "HT" ? "MT" : elapsed ? `${elapsed}'` : "LIVE"}
        </span>
      </span>
    );
  }
  if (DONE_ST.has(status)) {
    return <span className="text-[10px] font-mono text-on-surface-variant opacity-60">FT</span>;
  }
  return null;
}

function MatchCard({ m }: { m: ScoreMatch }) {
  const isLive = LIVE_ST.has(m.status);
  const isDone = DONE_ST.has(m.status);
  const hasScore = m.score.home !== null && m.score.away !== null;

  return (
    <Link
      href={`/match/${m.fixture_id}`}
      className={`flex items-center gap-sm px-md py-sm rounded-xl transition-all hover:bg-surface-container-high group ${
        isLive ? "border border-red-500/20 bg-red-500/5" : "border border-white/5"
      }`}
    >
      {/* Heure / statut */}
      <div className="w-12 flex flex-col items-center flex-shrink-0">
        {isLive ? (
          <StatusBadge status={m.status} elapsed={m.elapsed} />
        ) : isDone ? (
          <StatusBadge status={m.status} elapsed={null} />
        ) : (
          <span className="text-[11px] font-mono text-on-surface-variant">
            {new Date(m.heure).toLocaleTimeString("fr-CA", { hour: "2-digit", minute: "2-digit", timeZone: "America/Toronto" })}
          </span>
        )}
      </div>

      {/* Équipes */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-xs mb-[3px]">
          {m.home.logo && <img src={m.home.logo} alt="" className="w-4 h-4 object-contain flex-shrink-0" />}
          <span className={`text-sm truncate ${isDone && hasScore && m.score.home! > m.score.away! ? "font-bold text-on-surface" : "text-on-surface"}`}>
            {m.home.name}
          </span>
        </div>
        <div className="flex items-center gap-xs">
          {m.away.logo && <img src={m.away.logo} alt="" className="w-4 h-4 object-contain flex-shrink-0" />}
          <span className={`text-sm truncate ${isDone && hasScore && m.score.away! > m.score.home! ? "font-bold text-on-surface" : "text-on-surface-variant"}`}>
            {m.away.name}
          </span>
        </div>
      </div>

      {/* Score */}
      <div className="flex flex-col items-center min-w-[32px] flex-shrink-0">
        {hasScore ? (
          <>
            <span className={`font-mono font-bold text-base leading-tight ${isLive ? "text-red-400" : "text-on-surface"}`}>
              {m.score.home}
            </span>
            <span className={`font-mono font-bold text-base leading-tight ${isLive ? "text-red-400" : "text-on-surface"}`}>
              {m.score.away}
            </span>
          </>
        ) : (
          <span className="text-on-surface-variant opacity-30 font-mono text-sm">-</span>
        )}
      </div>

      {/* Flèche */}
      <span className="material-symbols-outlined text-[16px] text-on-surface-variant opacity-0 group-hover:opacity-50 transition-opacity flex-shrink-0">
        chevron_right
      </span>
    </Link>
  );
}

function LeagueGroup({ ligue, logo, matchs }: { ligue: string; logo?: string; matchs: ScoreMatch[] }) {
  return (
    <div className="mb-lg">
      <div className="flex items-center gap-sm mb-sm px-xs">
        {logo && <img src={logo} alt="" className="w-5 h-5 object-contain" />}
        <span className="text-xs font-bold text-on-surface-variant uppercase tracking-wider">{ligue}</span>
        <span className="text-xs text-on-surface-variant opacity-40">{matchs.length} match{matchs.length > 1 ? "s" : ""}</span>
      </div>
      <div className="flex flex-col gap-[3px]">
        {matchs.map((m) => <MatchCard key={m.fixture_id} m={m} />)}
      </div>
    </div>
  );
}

export default function ScoresPage() {
  const [date, setDate]     = useState(dateISO(new Date()));
  const [data, setData]     = useState<ScoresJour | null>(null);
  const [loading, setLoading] = useState(true);
  const [erreur, setErreur]   = useState<string | null>(null);

  const load = useCallback(async (d: string) => {
    setLoading(true);
    setErreur(null);
    try {
      const res = await getScores(d);
      setData(res);
    } catch (e) {
      setErreur(e instanceof Error ? e.message : "Erreur réseau");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(date); }, [date, load]);

  // Grouper par ligue
  const groupes = data
    ? Object.values(
        data.matchs.reduce<Record<number, { ligue_id: number; ligue: string; logo?: string; matchs: ScoreMatch[] }>>(
          (acc, m) => {
            if (!acc[m.ligue_id]) acc[m.ligue_id] = { ligue_id: m.ligue_id, ligue: m.ligue, logo: m.ligue_logo, matchs: [] };
            acc[m.ligue_id].matchs.push(m);
            return acc;
          },
          {}
        )
      )
    : [];

  const nbLive = data?.matchs.filter((m) => LIVE_ST.has(m.status)).length ?? 0;

  return (
    <>
      {/* Titre */}
      <div className="flex items-center justify-between mb-lg">
        <div>
          <h1 className="font-display-lg text-headline-lg font-black text-on-surface">Scores</h1>
          {nbLive > 0 && (
            <span className="flex items-center gap-xs mt-xs">
              <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
              <span className="text-xs text-red-400 font-semibold">{nbLive} match{nbLive > 1 ? "s" : ""} en direct</span>
            </span>
          )}
        </div>
      </div>

      {/* Navigation de date */}
      <div className="flex items-center gap-sm mb-xl bg-surface-container rounded-2xl p-xs">
        <button
          onClick={() => setDate(d => addDays(d, -1))}
          className="p-sm rounded-xl hover:bg-surface-container-high transition-colors text-on-surface-variant active:scale-95"
        >
          <Icon name="chevron_left" />
        </button>

        <div className="flex-1 flex justify-center">
          <span className="font-bold text-on-surface text-base">{labelDate(date)}</span>
        </div>

        <button
          onClick={() => setDate(dateISO(new Date()))}
          className="px-sm py-xs rounded-xl text-xs font-semibold text-primary hover:bg-primary/10 transition-colors"
        >
          Auj.
        </button>

        <button
          onClick={() => setDate(d => addDays(d, 1))}
          className="p-sm rounded-xl hover:bg-surface-container-high transition-colors text-on-surface-variant active:scale-95"
        >
          <Icon name="chevron_right" />
        </button>
      </div>

      {/* Contenu */}
      {loading && (
        <div className="flex items-center justify-center py-xl">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {erreur && (
        <div className="glass-card border-error/40 text-error p-lg rounded-xl text-sm">{erreur}</div>
      )}

      {!loading && !erreur && groupes.length === 0 && (
        <div className="text-center py-xl text-on-surface-variant">
          <Icon name="sports_soccer" style={{ fontSize: 48, opacity: 0.2 }} />
          <p className="mt-md text-sm">Aucun match ce jour-là dans nos ligues</p>
        </div>
      )}

      {!loading && groupes.map((g) => (
        <LeagueGroup key={g.ligue_id} ligue={g.ligue} logo={g.logo} matchs={g.matchs} />
      ))}
    </>
  );
}
