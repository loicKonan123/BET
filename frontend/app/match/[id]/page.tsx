"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import Icon from "../../components/Icon";
import { MatchDetail, getMatch } from "../../lib/api";

function Pastilles({ forme }: { forme: string }) {
  const couleur: Record<string, string> = {
    W: "bg-primary/25 text-primary",
    D: "bg-tertiary/25 text-tertiary",
    L: "bg-error/25 text-error",
  };
  const lettre: Record<string, string> = { W: "V", D: "N", L: "D" };
  return (
    <div className="flex gap-xs">
      {(forme || "-----").split("").map((c, i) => (
        <span key={i} className={`w-6 h-6 rounded flex items-center justify-center font-label-sm text-label-sm font-bold ${couleur[c] ?? "bg-white/5 text-on-surface-variant"}`}>
          {lettre[c] ?? "·"}
        </span>
      ))}
    </div>
  );
}

export default function MatchPage() {
  const params = useParams();
  const id = Number(params.id);
  const [m, setM] = useState<MatchDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [erreur, setErreur] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    getMatch(id)
      .then((d) => {
        if (d.erreur) setErreur(d.erreur);
        else setM(d);
      })
      .catch((e) => setErreur(e instanceof Error ? e.message : "Erreur réseau"))
      .finally(() => setLoading(false));
  }, [id]);

  const pct = (x: number) => `${Math.round(x * 100)}%`;

  return (
    <>
      <Link href="/analyses" className="inline-flex items-center gap-xs text-on-surface-variant hover:text-primary font-label-md text-label-md mb-lg transition-colors">
        <Icon name="arrow_back" style={{ fontSize: 18 }} /> Analyses
      </Link>

      {loading && (
        <div className="flex flex-col items-center justify-center py-xl">
          <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin mb-md" />
          <p className="text-primary font-label-md animate-pulse">ANALYSE EN COURS…</p>
        </div>
      )}

      {erreur && (
        <div className="glass-card border-error/40 text-error p-lg rounded-xl">Erreur : {erreur}</div>
      )}

      {m && (
        <>
          {/* En-tête match */}
          <div className="glass-card rounded-xl p-lg md:p-xl mb-lg">
            <div className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-widest mb-md">
              🏆 {m.ligue} · {new Date(m.date).toLocaleString("fr-FR", { dateStyle: "medium", timeStyle: "short" })}
            </div>
            <div className="flex items-center justify-between gap-md">
              <Equipe nom={m.home.name} logo={m.home.logo} />
              <div className="flex flex-col items-center">
                <span className="font-mono text-headline-md text-primary font-bold">
                  {m.buts_attendus.domicile} - {m.buts_attendus.exterieur}
                </span>
                <span className="font-label-sm text-label-sm text-on-surface-variant">buts attendus</span>
              </div>
              <Equipe nom={m.away.name} logo={m.away.logo} />
            </div>
          </div>

          {/* Conseil de paris */}
          {m.conseil && (
            <div className="glass-card rounded-xl p-lg mb-lg border-primary/40" style={{ boxShadow: "0 0 25px rgba(78,222,163,0.12)" }}>
              <div className="flex items-center gap-sm mb-md">
                <div className="w-10 h-10 rounded-lg bg-primary/15 flex items-center justify-center">
                  <Icon name="lightbulb" className="text-primary" />
                </div>
                <div>
                  <div className="font-label-sm text-label-sm uppercase tracking-widest text-on-surface-variant">Conseil de paris</div>
                  <div className="font-headline-sm text-headline-sm text-on-surface">{m.conseil.marche}</div>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-sm mb-md">
                <MiniStat label="Probabilité" value={pct(m.conseil.proba)} color="secondary" />
                <MiniStat label="Cote" value={m.conseil.cote ? m.conseil.cote.toFixed(2) : "—"} color="primary" />
                <MiniStat label="Value" value={`${m.conseil.value >= 0 ? "+" : ""}${Math.round(m.conseil.value * 100)}%`} color={m.conseil.value >= 0 ? "primary" : "error"} />
              </div>
              <p className="font-body-md text-body-md text-on-surface-variant">{m.conseil.raison}</p>
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-lg">
            {/* Probabilités + forme */}
            <div className="glass-card rounded-xl p-lg flex flex-col gap-lg">
              <div>
                <h2 className="font-headline-sm text-headline-sm text-on-surface mb-md">Résultat (1X2)</h2>
                <div className="flex h-3 rounded-full overflow-hidden bg-surface-container-highest">
                  <div className="bg-primary" style={{ width: pct(m.probabilites["1"] ?? 0) }} />
                  <div className="bg-outline" style={{ width: pct(m.probabilites["X"] ?? 0) }} />
                  <div className="bg-secondary" style={{ width: pct(m.probabilites["2"] ?? 0) }} />
                </div>
                <div className="flex justify-between mt-sm font-label-md text-label-md">
                  <span className="text-primary">Dom. {pct(m.probabilites["1"] ?? 0)}</span>
                  <span className="text-on-surface-variant">Nul {pct(m.probabilites["X"] ?? 0)}</span>
                  <span className="text-secondary">Ext. {pct(m.probabilites["2"] ?? 0)}</span>
                </div>
              </div>
              <div className="flex flex-col gap-sm pt-md border-t border-white/10">
                <div className="flex items-center justify-between">
                  <span className="font-label-md text-label-md text-on-surface-variant flex items-center gap-xs">
                    <Icon name="home" style={{ fontSize: 16 }} /> Forme domicile
                  </span>
                  <Pastilles forme={m.forme.domicile} />
                </div>
                <div className="flex items-center justify-between">
                  <span className="font-label-md text-label-md text-on-surface-variant flex items-center gap-xs">
                    <Icon name="flight" style={{ fontSize: 16 }} /> Forme extérieur
                  </span>
                  <Pastilles forme={m.forme.exterieur} />
                </div>
              </div>
            </div>

            {/* Tableau des marchés */}
            <div className="glass-card rounded-xl p-lg">
              <h2 className="font-headline-sm text-headline-sm text-on-surface mb-md">Tous les marchés</h2>
              {m.selections.length > 0 ? (
                <div className="flex flex-col gap-xs">
                  <div className="grid grid-cols-12 font-label-sm text-label-sm text-on-surface-variant px-sm pb-xs">
                    <span className="col-span-6">Marché</span>
                    <span className="col-span-2 text-right">Proba</span>
                    <span className="col-span-2 text-right">Cote</span>
                    <span className="col-span-2 text-right">Value</span>
                  </div>
                  {m.selections.map((s) => (
                    <div key={s.cle} className={`grid grid-cols-12 items-center px-sm py-sm rounded font-label-md text-label-md ${s.est_value_bet ? "bg-primary/10 border border-primary/20" : "bg-white/5"}`}>
                      <span className="col-span-6 text-on-surface">{s.marche}</span>
                      <span className="col-span-2 text-right text-secondary">{pct(s.proba)}</span>
                      <span className="col-span-2 text-right text-on-surface-variant">{s.cote.toFixed(2)}</span>
                      <span className={`col-span-2 text-right font-bold ${s.value >= 0 ? "text-primary" : "text-error"}`}>
                        {s.value >= 0 ? "+" : ""}{Math.round(s.value * 100)}%
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-on-surface-variant font-body-md">
                  Cotes indisponibles pour ce match (probabilités calculées affichées dans le 1X2).
                </p>
              )}
            </div>
          </div>

          <p className="font-label-sm text-label-sm text-on-surface-variant mt-xl">
            ⚠️ EDGE fournit une analyse et un conseil statistique — pas une certitude.
            Le pari se place sur Mise-o-jeu. Jouez de manière responsable.
          </p>
        </>
      )}
    </>
  );
}

function Equipe({ nom, logo }: { nom: string; logo?: string }) {
  return (
    <div className="flex flex-col items-center gap-sm flex-1 text-center">
      {logo ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={logo} alt={nom} className="w-14 h-14 object-contain" />
      ) : (
        <div className="w-14 h-14 rounded-full bg-surface-container-highest flex items-center justify-center">
          <Icon name="shield" className="text-on-surface-variant" />
        </div>
      )}
      <span className="font-body-md text-body-md text-on-surface font-semibold">{nom}</span>
    </div>
  );
}

function MiniStat({ label, value, color }: { label: string; value: string; color: "primary" | "secondary" | "error" }) {
  const cls = { primary: "text-primary", secondary: "text-secondary", error: "text-error" }[color];
  return (
    <div className="bg-white/5 rounded-lg p-sm flex flex-col items-center">
      <span className="font-label-sm text-label-sm text-on-surface-variant">{label}</span>
      <span className={`font-mono font-bold text-headline-sm ${cls}`}>{value}</span>
    </div>
  );
}
