"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import Icon from "../../components/Icon";
import { TeamDetail, TeamMatch, getTeam } from "../../lib/api";
import { dateHeureCanada } from "../../lib/date";

const RES_COLOR = { W: "bg-primary/25 text-primary", D: "bg-tertiary/25 text-tertiary", L: "bg-error/25 text-error" };
const RES_LABEL = { W: "V", D: "N", L: "D" };

function Pastilles({ forme }: { forme: string }) {
  return (
    <div className="flex gap-xs">
      {(forme || "-----").split("").map((c, i) => (
        <span key={i} className={`w-7 h-7 rounded-lg flex items-center justify-center font-bold text-sm ${RES_COLOR[c as keyof typeof RES_COLOR] ?? "bg-white/5 text-on-surface-variant"}`}>
          {RES_LABEL[c as keyof typeof RES_LABEL] ?? "·"}
        </span>
      ))}
    </div>
  );
}

function StatBox({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="bg-surface-container rounded-xl p-md flex flex-col items-center text-center">
      <span className="font-mono font-black text-2xl text-on-surface">{value}</span>
      {sub && <span className="font-mono text-xs text-primary">{sub}</span>}
      <span className="text-xs text-on-surface-variant mt-xs">{label}</span>
    </div>
  );
}

function MatchRow({ m }: { m: TeamMatch }) {
  return (
    <Link
      href={`/match/${m.fixture_id}`}
      className="flex items-center gap-sm py-sm px-sm rounded-xl hover:bg-surface-container-high transition-colors group border border-transparent hover:border-white/5"
    >
      {/* Résultat */}
      <span className={`w-7 h-7 rounded-lg flex items-center justify-center font-bold text-sm flex-shrink-0 ${RES_COLOR[m.resultat]}`}>
        {RES_LABEL[m.resultat]}
      </span>

      {/* Dom / Ext */}
      <span className={`text-[10px] font-semibold px-xs py-[2px] rounded flex-shrink-0 ${m.a_domicile ? "bg-primary/10 text-primary" : "bg-white/5 text-on-surface-variant"}`}>
        {m.a_domicile ? "DOM" : "EXT"}
      </span>

      {/* Adversaire */}
      <div className="flex items-center gap-xs flex-1 min-w-0">
        {m.adversaire_logo && <img src={m.adversaire_logo} alt="" className="w-5 h-5 object-contain flex-shrink-0" />}
        <span className="text-sm text-on-surface truncate">{m.adversaire}</span>
      </div>

      {/* Ligue */}
      <div className="hidden md:flex items-center gap-xs text-xs text-on-surface-variant opacity-60 flex-shrink-0">
        {m.ligue_logo && <img src={m.ligue_logo} alt="" className="w-4 h-4 object-contain" />}
        <span className="truncate max-w-[120px]">{m.ligue}</span>
      </div>

      {/* Score */}
      <span className="font-mono font-bold text-on-surface text-sm flex-shrink-0">{m.score}</span>

      {/* Buts pour/contre */}
      <span className={`font-mono text-xs flex-shrink-0 ${m.buts_pour > m.buts_contre ? "text-primary" : m.buts_pour < m.buts_contre ? "text-error" : "text-on-surface-variant"}`}>
        {m.buts_pour > m.buts_contre ? `+${m.buts_pour - m.buts_contre}` : m.buts_pour - m.buts_contre}
      </span>

      {/* Date */}
      <span className="text-xs text-on-surface-variant opacity-50 flex-shrink-0 hidden sm:block">
        {dateHeureCanada(m.date)}
      </span>

      <Icon name="chevron_right" style={{ fontSize: 16 }} className="text-on-surface-variant opacity-0 group-hover:opacity-50 transition-opacity flex-shrink-0" />
    </Link>
  );
}

export default function TeamPage() {
  const params  = useParams();
  const router  = useRouter();
  const teamId  = Number(params.id);

  const [team, setTeam]     = useState<TeamDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [erreur, setErreur]   = useState<string | null>(null);

  useEffect(() => {
    if (!teamId) return;
    getTeam(teamId)
      .then((d) => { if ((d as any).erreur) setErreur((d as any).erreur); else setTeam(d); })
      .catch((e) => setErreur(e instanceof Error ? e.message : "Erreur réseau"))
      .finally(() => setLoading(false));
  }, [teamId]);

  if (loading) return (
    <div className="flex items-center justify-center py-xl">
      <div className="w-10 h-10 border-4 border-primary border-t-transparent rounded-full animate-spin" />
    </div>
  );
  if (erreur) return <div className="glass-card border-error/40 text-error p-lg rounded-xl">{erreur}</div>;
  if (!team) return null;

  const { stats } = team;
  const winRate = stats.matchs > 0 ? Math.round((stats.victoires / stats.matchs) * 100) : 0;

  return (
    <>
      <button onClick={() => router.back()} className="inline-flex items-center gap-xs text-on-surface-variant hover:text-primary font-label-md text-label-md mb-lg transition-colors">
        <Icon name="arrow_back" style={{ fontSize: 18 }} /> Retour
      </button>

      {/* Header équipe */}
      <div className="glass-card rounded-2xl p-lg md:p-xl mb-lg">
        <div className="flex items-center gap-lg">
          {team.logo
            ? <img src={team.logo} alt={team.nom} className="w-20 h-20 object-contain flex-shrink-0" />
            : <div className="w-20 h-20 rounded-full bg-surface-container-highest flex items-center justify-center"><Icon name="shield" style={{ fontSize: 36 }} className="text-on-surface-variant" /></div>
          }
          <div>
            <h1 className="font-display-lg text-headline-lg font-black text-on-surface">{team.nom}</h1>
            <div className="flex items-center gap-sm mt-xs flex-wrap">
              {team.pays && (
                <span className="text-sm text-on-surface-variant flex items-center gap-xs">
                  <Icon name="public" style={{ fontSize: 14 }} /> {team.pays}
                </span>
              )}
              {team.stade && (
                <span className="text-sm text-on-surface-variant flex items-center gap-xs">
                  <Icon name="stadium" style={{ fontSize: 14 }} /> {team.stade}{team.ville ? `, ${team.ville}` : ""}
                </span>
              )}
            </div>
            <div className="mt-md">
              <p className="text-xs text-on-surface-variant mb-xs">Forme récente</p>
              <Pastilles forme={team.forme} />
            </div>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-sm mb-lg">
        <StatBox label="Taux de victoire" value={`${winRate}%`} />
        <StatBox label="Bilan (15 matchs)" value={`${stats.victoires}V ${stats.nuls}N ${stats.defaites}D`} />
        <StatBox label="Buts marqués / match" value={stats.moy_bp} sub={`${stats.buts_pour} total`} />
        <StatBox label="Buts concédés / match" value={stats.moy_bc} sub={`${stats.buts_contre} total`} />
      </div>

      {/* Historique des matchs */}
      <div className="glass-card rounded-xl p-lg">
        <h2 className="font-headline-sm text-headline-sm text-on-surface mb-md flex items-center gap-sm">
          <Icon name="history" className="text-secondary" />
          15 derniers matchs
        </h2>
        <div className="flex flex-col gap-[2px]">
          {team.matchs.length > 0
            ? team.matchs.map((m) => <MatchRow key={m.fixture_id} m={m} />)
            : <p className="text-on-surface-variant font-body-md">Aucun match récent trouvé.</p>
          }
        </div>
      </div>
    </>
  );
}
