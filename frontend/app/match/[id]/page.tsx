"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import Icon from "../../components/Icon";
import { AnalyseIA, LigneClassement, MatchDetail, getAnalyseIA, getMatch } from "../../lib/api";
import { dateHeureCanada } from "../../lib/date";

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
  const [ia, setIa] = useState<AnalyseIA | null>(null);
  const [iaLoading, setIaLoading] = useState(false);
  const [iaErreur, setIaErreur] = useState<string | null>(null);

  async function demanderIA(force = false) {
    setIaLoading(true);
    setIaErreur(null);
    try {
      const d = await getAnalyseIA(id, force);
      if (d.erreur) setIaErreur(d.erreur);
      else setIa(d);
    } catch (e) {
      setIaErreur(e instanceof Error ? e.message : "Erreur réseau");
    } finally {
      setIaLoading(false);
    }
  }

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
              🏆 {m.ligue} · {dateHeureCanada(m.date)}
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

          {/* Analyse de l'expert IA (DeepSeek) */}
          <div className="glass-card rounded-xl p-lg mb-lg">
            <div className="flex items-center justify-between gap-md mb-md flex-wrap">
              <div className="flex items-center gap-sm">
                <div className="w-10 h-10 rounded-lg bg-secondary-container/30 flex items-center justify-center">
                  <Icon name="neurology" className="text-secondary" />
                </div>
                <div>
                  <div className="font-label-sm text-label-sm uppercase tracking-widest text-on-surface-variant">
                    Cerveau analyste
                  </div>
                  <div className="font-headline-sm text-headline-sm text-on-surface">
                    Analyse de l&apos;expert IA
                  </div>
                </div>
              </div>
              {!ia && (
                <button
                  onClick={() => demanderIA()}
                  disabled={iaLoading}
                  className="flex items-center gap-sm bg-secondary-container text-on-secondary-container font-label-md text-label-md px-lg py-sm rounded-lg hover:opacity-90 transition-all active:scale-95 disabled:opacity-50"
                >
                  {iaLoading ? (
                    <>
                      <span className="w-4 h-4 border-2 border-on-secondary-container border-t-transparent rounded-full animate-spin" />
                      L&apos;expert analyse…
                    </>
                  ) : (
                    <>
                      <Icon name="auto_awesome" style={{ fontSize: 18 }} />
                      Demander l&apos;analyse
                    </>
                  )}
                </button>
              )}
              {ia && (
                <button
                  onClick={() => demanderIA(true)}
                  disabled={iaLoading}
                  title="Forcer une nouvelle analyse"
                  className="flex items-center gap-xs bg-white/5 hover:bg-white/10 text-on-surface-variant font-label-sm text-label-sm px-md py-sm rounded-lg transition-all disabled:opacity-50"
                >
                  <Icon
                    name="refresh"
                    style={{ fontSize: 16 }}
                    className={iaLoading ? "animate-spin" : ""}
                  />
                  Rafraîchir
                </button>
              )}
            </div>

            {iaErreur && <p className="text-error font-body-md">Erreur : {iaErreur}</p>}

            {!ia && !iaLoading && !iaErreur && (
              <p className="font-body-md text-body-md text-on-surface-variant">
                Lance une analyse approfondie : l&apos;IA croise les probabilités, la
                forme, les blessures et l&apos;historique pour un avis nuancé (~20s).
              </p>
            )}

            {iaLoading && (
              <p className="font-body-md text-body-md text-on-surface-variant animate-pulse">
                L&apos;expert IA étudie le dossier (probas, blessures, H2H)…
              </p>
            )}

            {ia && (
              <div className="flex flex-col gap-md">
                <p className="font-body-lg text-body-lg text-on-surface">{ia.analyse}</p>

                {ia.points_cles?.length > 0 && (
                  <div>
                    <div className="font-label-sm text-label-sm uppercase tracking-widest text-on-surface-variant mb-xs">
                      Points clés
                    </div>
                    <ul className="flex flex-col gap-xs">
                      {ia.points_cles.map((p, i) => (
                        <li key={i} className="flex items-start gap-sm font-body-md text-body-md text-on-surface">
                          <Icon name="check_circle" className="text-primary mt-0.5" style={{ fontSize: 16 }} />
                          <span>{p}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {ia.facteurs_risque?.length > 0 && (
                  <div>
                    <div className="font-label-sm text-label-sm uppercase tracking-widest text-on-surface-variant mb-xs">
                      Facteurs de risque
                    </div>
                    <ul className="flex flex-col gap-xs">
                      {ia.facteurs_risque.map((p, i) => (
                        <li key={i} className="flex items-start gap-sm font-body-md text-body-md text-on-surface">
                          <Icon name="warning" className="text-tertiary mt-0.5" style={{ fontSize: 16 }} />
                          <span>{p}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {ia.recommandation && (
                  <div className="bg-secondary-container/20 border border-secondary/20 rounded-lg p-md">
                    <div className="flex items-center justify-between mb-xs">
                      <span className="font-headline-sm text-headline-sm text-secondary">
                        {ia.recommandation.marche}
                      </span>
                      <span className="font-label-sm text-label-sm uppercase tracking-widest text-on-surface-variant">
                        confiance {ia.recommandation.confiance}
                      </span>
                    </div>
                    <p className="font-body-md text-body-md text-on-surface-variant">
                      {ia.recommandation.justification}
                    </p>
                  </div>
                )}

                {ia.nuance && (
                  <div className="flex items-start gap-sm font-body-md text-body-md text-on-surface-variant">
                    <Icon
                      name={ia.accord_avec_modele ? "thumb_up" : "balance"}
                      className={ia.accord_avec_modele ? "text-primary" : "text-tertiary"}
                      style={{ fontSize: 16 }}
                    />
                    <span>
                      {ia.accord_avec_modele === false && (
                        <strong className="text-tertiary">Nuance vs modèle : </strong>
                      )}
                      {ia.nuance}
                    </span>
                  </div>
                )}

                <span className="font-label-sm text-label-sm text-on-surface-variant/60 self-end">
                  Généré par {ia.modele}
                  {ia.cache ? " · depuis le cache" : ""}
                </span>
              </div>
            )}
          </div>

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

          {/* Pronostic croisé (notre modèle vs API-Football) */}
          {m.prediction_api && (
            <div className="glass-card rounded-xl p-lg mt-lg">
              <h2 className="font-headline-sm text-headline-sm text-on-surface mb-md flex items-center gap-sm">
                <Icon name="compare_arrows" className="text-secondary" /> Pronostic croisé
              </h2>
              {m.prediction_api.pourcentages && (
                <div className="grid grid-cols-3 gap-sm mb-md text-center">
                  {(["home", "draw", "away"] as const).map((k, i) => {
                    const labels = ["Domicile", "Nul", "Extérieur"];
                    const nous = [m.probabilites["1"], m.probabilites["X"], m.probabilites["2"]][i] ?? 0;
                    return (
                      <div key={k} className="bg-white/5 rounded-lg p-sm">
                        <div className="font-label-sm text-label-sm text-on-surface-variant mb-xs">{labels[i]}</div>
                        <div className="font-mono text-primary font-bold">{Math.round(nous * 100)}%</div>
                        <div className="font-label-sm text-label-sm text-on-surface-variant/60">EDGE</div>
                        <div className="font-mono text-secondary font-bold mt-xs">{m.prediction_api!.pourcentages![k]}</div>
                        <div className="font-label-sm text-label-sm text-on-surface-variant/60">API</div>
                      </div>
                    );
                  })}
                </div>
              )}
              {m.prediction_api.conseil && (
                <p className="font-body-md text-body-md text-on-surface-variant">
                  <span className="text-on-surface-variant/60">Conseil API-Football : </span>
                  <span className="text-on-surface">{m.prediction_api.conseil}</span>
                </p>
              )}
            </div>
          )}

          {/* Classement par groupe (2 équipes surlignées) */}
          {m.classement?.groupes && m.classement.groupes.length > 0 && (
            <div className="glass-card rounded-xl p-lg mt-lg overflow-x-auto">
              <h2 className="font-headline-sm text-headline-sm text-on-surface mb-md flex items-center gap-sm">
                <Icon name="leaderboard" className="text-tertiary" /> Classement — {m.ligue}
              </h2>
              <div className="flex flex-col gap-lg">
                {m.classement.groupes.map((g, gi) => (
                  <div key={gi}>
                    {m.classement!.groupes.length > 1 && (
                      <div className="font-label-md text-label-md text-tertiary uppercase tracking-widest mb-sm">
                        {g.nom}
                      </div>
                    )}
                    <GroupeTable
                      lignes={g.lignes}
                      homeId={m.classement!.home_id}
                      awayId={m.classement!.away_id}
                    />
                  </div>
                ))}
              </div>
              <div className="flex gap-lg mt-md font-label-sm text-label-sm">
                <span className="flex items-center gap-xs text-on-surface-variant">
                  <span className="w-3 h-3 rounded bg-primary/40" /> {m.home.name}
                </span>
                <span className="flex items-center gap-xs text-on-surface-variant">
                  <span className="w-3 h-3 rounded bg-secondary/40" /> {m.away.name}
                </span>
              </div>
            </div>
          )}

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

function GroupeTable({
  lignes,
  homeId,
  awayId,
}: {
  lignes: LigneClassement[];
  homeId: number;
  awayId: number;
}) {
  return (
    <table className="w-full text-left border-collapse">
      <thead>
        <tr className="font-label-sm text-label-sm text-on-surface-variant">
          <th className="py-xs pr-sm">#</th>
          <th className="py-xs">Équipe</th>
          <th className="py-xs px-sm text-center">J</th>
          <th className="py-xs px-sm text-center hidden sm:table-cell">Diff</th>
          <th className="py-xs px-sm text-center">Pts</th>
          <th className="py-xs pl-sm hidden md:table-cell">Forme</th>
        </tr>
      </thead>
      <tbody>
        {lignes.map((l) => {
          const dom = l.equipe_id === homeId;
          const ext = l.equipe_id === awayId;
          const surligne = dom ? "bg-primary/15" : ext ? "bg-secondary/15" : "";
          const nomCls = dom
            ? "text-primary font-semibold"
            : ext
            ? "text-secondary font-semibold"
            : "text-on-surface";
          return (
            <tr key={l.equipe_id} className={`border-t border-white/5 ${surligne}`}>
              <td className="py-sm pr-sm font-mono text-on-surface-variant">{l.rang}</td>
              <td className="py-sm">
                <span className="flex items-center gap-sm">
                  {l.logo && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={l.logo} alt="" className="w-5 h-5 object-contain" />
                  )}
                  <span className={`font-body-md text-body-md ${nomCls}`}>{l.equipe}</span>
                </span>
              </td>
              <td className="py-sm px-sm text-center text-on-surface-variant font-mono">{l.joues}</td>
              <td className="py-sm px-sm text-center text-on-surface-variant font-mono hidden sm:table-cell">
                {l.diff != null && l.diff > 0 ? `+${l.diff}` : l.diff}
              </td>
              <td className="py-sm px-sm text-center font-mono font-bold text-on-surface">{l.points}</td>
              <td className="py-sm pl-sm hidden md:table-cell">
                <Pastilles forme={(l.forme || "").slice(-5)} />
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
