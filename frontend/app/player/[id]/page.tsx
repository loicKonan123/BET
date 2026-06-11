"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import Icon from "../../components/Icon";
import { PlayerDetail, getPlayer } from "../../lib/api";

function StatBox({ label, value, icon }: { label: string; value: string | number; icon?: string }) {
  return (
    <div className="bg-surface-container rounded-xl p-md flex flex-col items-center text-center">
      {icon && <Icon name={icon} className="text-on-surface-variant mb-xs" style={{ fontSize: 20 }} />}
      <span className="font-mono font-black text-2xl text-on-surface">{value}</span>
      <span className="text-xs text-on-surface-variant mt-xs">{label}</span>
    </div>
  );
}

export default function PlayerPage() {
  const params   = useParams();
  const router   = useRouter();
  const playerId = Number(params.id);

  const [player, setPlayer] = useState<PlayerDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [erreur, setErreur]   = useState<string | null>(null);

  useEffect(() => {
    if (!playerId) return;
    getPlayer(playerId)
      .then((d) => { if ((d as any).erreur) setErreur((d as any).erreur); else setPlayer(d); })
      .catch((e) => setErreur(e instanceof Error ? e.message : "Erreur réseau"))
      .finally(() => setLoading(false));
  }, [playerId]);

  if (loading) return (
    <div className="flex items-center justify-center py-xl">
      <div className="w-10 h-10 border-4 border-primary border-t-transparent rounded-full animate-spin" />
    </div>
  );
  if (erreur) return <div className="glass-card border-error/40 text-error p-lg rounded-xl">{erreur}</div>;
  if (!player) return null;

  const age = player.naissance
    ? Math.floor((Date.now() - new Date(player.naissance).getTime()) / (365.25 * 24 * 3600 * 1000))
    : null;

  const note = player.stats.note ? parseFloat(player.stats.note) : null;
  const noteColor = note ? (note >= 7 ? "text-primary" : note >= 6 ? "text-tertiary" : "text-error") : "text-on-surface-variant";

  return (
    <>
      <button onClick={() => router.back()} className="inline-flex items-center gap-xs text-on-surface-variant hover:text-primary font-label-md text-label-md mb-lg transition-colors">
        <Icon name="arrow_back" style={{ fontSize: 18 }} /> Retour
      </button>

      {/* Header joueur */}
      <div className="glass-card rounded-2xl p-lg md:p-xl mb-lg">
        <div className="flex items-center gap-lg">
          {/* Photo */}
          <div className="relative flex-shrink-0">
            {player.photo
              ? <img src={player.photo} alt={player.nom} className="w-24 h-24 rounded-2xl object-cover bg-surface-container-highest" />
              : <div className="w-24 h-24 rounded-2xl bg-surface-container-highest flex items-center justify-center"><Icon name="person" style={{ fontSize: 40 }} className="text-on-surface-variant" /></div>
            }
            {note && (
              <span className={`absolute -bottom-2 -right-2 w-8 h-8 rounded-full bg-surface border-2 border-surface-container-high flex items-center justify-center font-mono font-bold text-xs ${noteColor}`}>
                {note.toFixed(1)}
              </span>
            )}
          </div>

          {/* Infos */}
          <div className="flex-1 min-w-0">
            <h1 className="font-display-lg text-headline-lg font-black text-on-surface">{player.nom}</h1>
            <div className="flex items-center gap-sm mt-xs flex-wrap">
              {player.poste && (
                <span className="px-sm py-[2px] rounded-full bg-primary/10 text-primary text-xs font-semibold">
                  {player.poste}
                </span>
              )}
              {player.nationalite && <span className="text-sm text-on-surface-variant">{player.nationalite}</span>}
              {age && <span className="text-sm text-on-surface-variant">{age} ans</span>}
              {player.taille && <span className="text-sm text-on-surface-variant">{player.taille}</span>}
            </div>

            {/* Équipe actuelle */}
            {player.equipe && (
              <Link href={`/team/${player.equipe_id}`} className="inline-flex items-center gap-sm mt-md hover:text-primary transition-colors">
                {player.equipe_logo && <img src={player.equipe_logo} alt="" className="w-6 h-6 object-contain" />}
                <span className="font-semibold text-on-surface">{player.equipe}</span>
                <Icon name="arrow_forward" style={{ fontSize: 14 }} className="text-on-surface-variant" />
              </Link>
            )}
          </div>
        </div>
      </div>

      {/* Stats saison */}
      <div className="mb-md flex items-center justify-between">
        <h2 className="font-headline-sm text-headline-sm text-on-surface">Saison {player.saison}/{player.saison + 1}</h2>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-sm mb-lg">
        <StatBox label="Matchs joués" value={player.stats.matchs} icon="sports_soccer" />
        <StatBox label="Buts" value={player.stats.buts} icon="sports_score" />
        <StatBox label="Passes décisives" value={player.stats.passes_decisives} icon="assistant" />
        <StatBox label="Minutes jouées" value={player.stats.minutes} icon="timer" />
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-sm">
        <StatBox label="Titularisations" value={player.stats.titularisations} />
        <StatBox label="Passes (total)" value={player.stats.passes} />
        <StatBox label="Cartons jaunes" value={player.stats.cartons_jaunes} />
        <StatBox label="Cartons rouges" value={player.stats.cartons_rouges} />
      </div>

      {/* Naissance */}
      {player.naissance && (
        <p className="mt-lg text-xs text-on-surface-variant text-center opacity-50">
          Né le {new Date(player.naissance).toLocaleDateString("fr-CA", { day: "numeric", month: "long", year: "numeric" })}
        </p>
      )}
    </>
  );
}
