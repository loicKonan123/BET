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

function norm(s: string) {
  return s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
}

function jourCourt(iso: string) {
  const d = new Date(iso + "T12:00:00Z");
  return {
    jour: d.toLocaleDateString("fr-CA", { weekday: "short" }).replace(".", ""),
    num: d.getUTCDate(),
  };
}

function LeagueGroup({
  ligue, logo, flag, pays, matchs, collapsed, onToggle,
}: {
  ligue: string; logo?: string; flag?: string | null; pays?: string | null;
  matchs: ScoreMatch[]; collapsed: boolean; onToggle: () => void;
}) {
  return (
    <div className="mb-md">
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-sm mb-sm px-sm py-xs rounded-lg hover:bg-surface-container-high transition-colors"
      >
        {logo ? <img src={logo} alt="" className="w-5 h-5 object-contain flex-shrink-0" />
              : flag && <img src={flag} alt="" className="w-5 h-4 object-cover rounded-sm flex-shrink-0" />}
        <span className="text-xs font-bold text-on-surface uppercase tracking-wider truncate">{ligue}</span>
        {pays && <span className="text-[10px] text-on-surface-variant/50 truncate hidden sm:inline">· {pays}</span>}
        <span className="text-[11px] font-mono text-on-surface-variant/50">{matchs.length}</span>
        <Icon name={collapsed ? "expand_more" : "expand_less"}
          className="ml-auto text-on-surface-variant/50" style={{ fontSize: 18 }} />
      </button>
      {!collapsed && (
        <div className="flex flex-col gap-[3px]">
          {matchs.map((m) => <MatchCard key={m.fixture_id} m={m} />)}
        </div>
      )}
    </div>
  );
}

type Statut = "tous" | "live" | "avenir" | "termine";
const estAvenir = (s: string) => !LIVE_ST.has(s) && !DONE_ST.has(s);

export default function ScoresPage() {
  const [date, setDate]     = useState(dateISO(new Date()));
  const [data, setData]     = useState<ScoresJour | null>(null);
  const [loading, setLoading] = useState(true);
  const [erreur, setErreur]   = useState<string | null>(null);

  // Filtres / sélection
  const [q, setQ]             = useState("");
  const [statut, setStatut]   = useState<Statut>("tous");
  const [ligueSel, setLigueSel] = useState<number | null>(null);
  const [replies, setReplies] = useState<Set<number>>(new Set());

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

  useEffect(() => { load(date); setLigueSel(null); }, [date, load]);

  const matchs = data?.matchs ?? [];

  // 1 — Recherche (équipe ou compétition)
  const nq = norm(q.trim());
  const apresRecherche = nq
    ? matchs.filter((m) => norm(`${m.home.name} ${m.away.name} ${m.ligue} ${m.pays ?? ""}`).includes(nq))
    : matchs;

  // Compteurs par statut (sur le résultat de recherche)
  const cnt = {
    tous: apresRecherche.length,
    live: apresRecherche.filter((m) => LIVE_ST.has(m.status)).length,
    avenir: apresRecherche.filter((m) => estAvenir(m.status)).length,
    termine: apresRecherche.filter((m) => DONE_ST.has(m.status)).length,
  };

  // 2 — Filtre de statut
  const apresStatut = apresRecherche.filter((m) =>
    statut === "tous" ? true
    : statut === "live" ? LIVE_ST.has(m.status)
    : statut === "termine" ? DONE_ST.has(m.status)
    : estAvenir(m.status));

  // 3 — Compétitions présentes (puces)
  const comps = Object.values(
    apresStatut.reduce<Record<number, { id: number; nom: string; logo?: string; n: number }>>(
      (acc, m) => {
        if (!acc[m.ligue_id]) acc[m.ligue_id] = { id: m.ligue_id, nom: m.ligue, logo: m.ligue_logo, n: 0 };
        acc[m.ligue_id].n++;
        return acc;
      }, {})
  ).sort((a, b) => b.n - a.n || a.nom.localeCompare(b.nom));

  // 4 — Filtre par compétition
  const visibles = ligueSel ? apresStatut.filter((m) => m.ligue_id === ligueSel) : apresStatut;

  // 5 — Regroupement par compétition
  const groupes = Object.values(
    visibles.reduce<Record<number, { ligue_id: number; ligue: string; logo?: string; flag?: string | null; pays?: string | null; matchs: ScoreMatch[] }>>(
      (acc, m) => {
        if (!acc[m.ligue_id]) acc[m.ligue_id] = { ligue_id: m.ligue_id, ligue: m.ligue, logo: m.ligue_logo, flag: m.pays_flag, pays: m.pays, matchs: [] };
        acc[m.ligue_id].matchs.push(m);
        return acc;
      }, {})
  ).sort((a, b) => (b.matchs.length - a.matchs.length) || a.ligue.localeCompare(b.ligue));

  const toggleGroupe = (id: number) =>
    setReplies((s) => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n; });

  const jours = [-3, -2, -1, 0, 1, 2, 3].map((o) => addDays(date, o));
  const auj = dateISO(new Date());

  const ChipStatut = ({ v, label }: { v: Statut; label: string }) => (
    <button
      onClick={() => setStatut(v)}
      className={`flex items-center gap-xs px-md py-xs rounded-full text-xs font-semibold whitespace-nowrap transition-colors ${
        statut === v ? "bg-primary text-on-primary" : "bg-surface-container-high text-on-surface-variant hover:bg-surface-container-highest"
      }`}
    >
      {v === "live" && <span className={`w-1.5 h-1.5 rounded-full ${statut === v ? "bg-on-primary" : "bg-red-500"} ${cnt.live ? "animate-pulse" : ""}`} />}
      {label}
      <span className={statut === v ? "opacity-70" : "opacity-40"}>{cnt[v]}</span>
    </button>
  );

  return (
    <>
      {/* Titre */}
      <div className="flex items-center justify-between mb-lg">
        <h1 className="font-display-lg text-headline-lg font-black text-on-surface">Scores</h1>
        {cnt.live > 0 && (
          <span className="flex items-center gap-xs">
            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
            <span className="text-xs text-red-400 font-semibold">{cnt.live} en direct</span>
          </span>
        )}
      </div>

      {/* Bande de jours + calendrier */}
      <div className="flex items-center gap-xs mb-md">
        <button onClick={() => setDate((d) => addDays(d, -7))}
          className="p-sm rounded-xl hover:bg-surface-container-high text-on-surface-variant active:scale-95">
          <Icon name="chevron_left" />
        </button>
        <div className="flex-1 grid grid-cols-7 gap-xs">
          {jours.map((d) => {
            const sel = d === date;
            const { jour, num } = jourCourt(d);
            return (
              <button key={d} onClick={() => setDate(d)}
                className={`flex flex-col items-center py-xs rounded-xl transition-colors ${
                  sel ? "bg-primary text-on-primary" : "hover:bg-surface-container-high text-on-surface-variant"
                }`}>
                <span className="text-[10px] uppercase opacity-70">{d === auj ? "Auj" : jour}</span>
                <span className="text-sm font-bold">{num}</span>
              </button>
            );
          })}
        </div>
        <button onClick={() => setDate((d) => addDays(d, 7))}
          className="p-sm rounded-xl hover:bg-surface-container-high text-on-surface-variant active:scale-95">
          <Icon name="chevron_right" />
        </button>
        <label className="p-sm rounded-xl hover:bg-surface-container-high text-on-surface-variant cursor-pointer relative">
          <Icon name="calendar_month" />
          <input type="date" value={date} onChange={(e) => e.target.value && setDate(e.target.value)}
            className="absolute inset-0 opacity-0 cursor-pointer" />
        </label>
      </div>

      {/* Recherche */}
      <div className="relative mb-md">
        <Icon name="search" className="absolute left-md top-1/2 -translate-y-1/2 text-on-surface-variant/50" style={{ fontSize: 18 }} />
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Chercher une équipe ou une compétition…"
          className="w-full bg-surface-container rounded-xl pl-[42px] pr-md py-sm text-sm text-on-surface placeholder:text-on-surface-variant/50 border border-white/5 focus:outline-none focus:border-primary/40"
        />
        {q && (
          <button onClick={() => setQ("")} className="absolute right-md top-1/2 -translate-y-1/2 text-on-surface-variant/50 hover:text-on-surface">
            <Icon name="close" style={{ fontSize: 18 }} />
          </button>
        )}
      </div>

      {/* Filtres de statut */}
      <div className="flex gap-xs mb-md overflow-x-auto pb-xs">
        <ChipStatut v="tous" label="Tous" />
        <ChipStatut v="live" label="En direct" />
        <ChipStatut v="avenir" label="À venir" />
        <ChipStatut v="termine" label="Terminés" />
      </div>

      {/* Filtre par compétition */}
      {comps.length > 1 && (
        <div className="flex gap-xs mb-lg overflow-x-auto pb-xs">
          <button onClick={() => setLigueSel(null)}
            className={`px-md py-xs rounded-full text-xs font-semibold whitespace-nowrap transition-colors ${
              ligueSel === null ? "bg-on-surface/90 text-surface" : "bg-surface-container-high text-on-surface-variant hover:bg-surface-container-highest"
            }`}>
            Toutes
          </button>
          {comps.map((c) => (
            <button key={c.id} onClick={() => setLigueSel(ligueSel === c.id ? null : c.id)}
              className={`flex items-center gap-xs px-md py-xs rounded-full text-xs font-semibold whitespace-nowrap transition-colors ${
                ligueSel === c.id ? "bg-on-surface/90 text-surface" : "bg-surface-container-high text-on-surface-variant hover:bg-surface-container-highest"
              }`}>
              {c.logo && <img src={c.logo} alt="" className="w-3.5 h-3.5 object-contain" />}
              {c.nom}
              <span className="opacity-50">{c.n}</span>
            </button>
          ))}
        </div>
      )}

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
          <p className="mt-md text-sm">
            {matchs.length === 0 ? "Aucun match ce jour-là dans nos ligues" : "Aucun match ne correspond aux filtres"}
          </p>
        </div>
      )}

      {!loading && groupes.map((g) => (
        <LeagueGroup
          key={g.ligue_id}
          ligue={g.ligue}
          logo={g.logo}
          flag={g.flag}
          pays={g.pays}
          matchs={g.matchs}
          collapsed={replies.has(g.ligue_id)}
          onToggle={() => toggleGroupe(g.ligue_id)}
        />
      ))}
    </>
  );
}
