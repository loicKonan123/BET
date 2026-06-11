"use client";

import Link from "next/link";
import { useLiveMatches } from "../hooks/useLiveMatches";

function statusLabel(status: string, elapsed: number | null) {
  if (status === "HT") return "Mi-temps";
  if (status === "ET") return "Prol.";
  if (status === "P")  return "Tirs au but";
  if (elapsed)        return `${elapsed}'`;
  return status;
}

export default function LiveWidget() {
  const { matches, loading } = useLiveMatches();

  if (loading || matches.length === 0) return null;

  return (
    <div className="mt-sm">
      {/* En-tête */}
      <div className="flex items-center gap-xs px-md mb-xs">
        <span
          className="w-2 h-2 rounded-full bg-red-500"
          style={{ animation: "pulse 1.5s ease-in-out infinite" }}
        />
        <span className="text-[10px] font-bold text-red-400 tracking-widest uppercase">
          Live
        </span>
        <span className="text-[10px] text-on-surface-variant opacity-60">
          {matches.length} match{matches.length > 1 ? "s" : ""}
        </span>
      </div>

      {/* Cartes matchs */}
      <div className="flex flex-col gap-[2px] px-xs">
        {matches.map((m) => (
          <Link
            key={m.fixture_id}
            href={`/match/${m.fixture_id}`}
            className="flex items-center gap-xs px-sm py-[6px] rounded-lg hover:bg-surface-container-high transition-colors group"
          >
            {/* Score + minute */}
            <div className="flex flex-col items-center min-w-[42px]">
              <span className="font-mono font-bold text-sm text-on-surface leading-none">
                {m.score.home} <span className="text-on-surface-variant opacity-40">-</span> {m.score.away}
              </span>
              <span className="text-[9px] text-red-400 font-semibold mt-[1px]">
                {statusLabel(m.status, m.elapsed)}
              </span>
            </div>

            {/* Équipes */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-[4px]">
                {m.home.logo && (
                  <img src={m.home.logo} alt="" className="w-3 h-3 object-contain flex-shrink-0" />
                )}
                <span className="text-[11px] text-on-surface truncate leading-none">
                  {m.home.name}
                </span>
              </div>
              <div className="flex items-center gap-[4px] mt-[2px]">
                {m.away.logo && (
                  <img src={m.away.logo} alt="" className="w-3 h-3 object-contain flex-shrink-0" />
                )}
                <span className="text-[11px] text-on-surface-variant truncate leading-none">
                  {m.away.name}
                </span>
              </div>
            </div>

            {/* Flèche */}
            <span className="material-symbols-outlined text-[14px] text-on-surface-variant opacity-0 group-hover:opacity-60 transition-opacity">
              chevron_right
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}
