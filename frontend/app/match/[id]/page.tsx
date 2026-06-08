"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import Icon from "../../components/Icon";
import { AnalyseIA, CompoEquipe, DernierMatch, LigneClassement, MatchDetail, getAnalyseIA, getMatch } from "../../lib/api";
import { dateHeureCanada } from "../../lib/date";
import { useTicketBuilder } from "../../lib/useTicketBuilder";

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
  const [tabClassement, setTabClassement] = useState(0);
  const { picks, add, remove } = useTicketBuilder();

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
        if (d.erreur) { setErreur(d.erreur); return; }
        setM(d);
        // Sélectionner automatiquement le groupe qui contient les deux équipes
        if (d.classement?.groupes) {
          const homeId = d.home?.id ?? d.classement.home_id;
          const awayId = d.away?.id ?? d.classement.away_id;
          const idx = d.classement.groupes.findIndex((g) => {
            const ids = new Set(g.lignes.map((l) => l.equipe_id));
            return ids.has(homeId) && ids.has(awayId);
          });
          if (idx >= 0) setTabClassement(idx);
        }
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

                {ia.cache && (
                  <span className="font-label-sm text-label-sm text-on-surface-variant/60 self-end">
                    Depuis le cache
                  </span>
                )}
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
                  <div className="grid grid-cols-13 font-label-sm text-label-sm text-on-surface-variant px-sm pb-xs" style={{ gridTemplateColumns: "1fr auto auto auto auto" }}>
                    <span>Marché</span>
                    <span className="text-right pl-md">Proba</span>
                    <span className="text-right pl-md">Cote</span>
                    <span className="text-right pl-md">Value</span>
                    <span className="pl-sm" />
                  </div>
                  {m.selections.map((s) => {
                    const inPicks = picks.some((p) => p.fixture_id === m.fixture_id && p.cle === s.cle);
                    const isConseil = m.conseil?.marche === s.marche;
                    const rowCls = isConseil
                      ? "bg-tertiary/15 border border-tertiary/40 shadow-[0_0_12px_rgba(var(--md-sys-color-tertiary)/0.15)]"
                      : s.est_value_bet
                      ? "bg-primary/10 border border-primary/20"
                      : "bg-white/5";
                    return (
                      <div key={s.cle} style={{ gridTemplateColumns: "1fr auto auto auto auto" }} className={`grid items-center px-sm py-sm rounded font-label-md text-label-md ${rowCls}`}>
                        <span className={`flex items-center gap-xs ${isConseil ? "text-tertiary font-semibold" : "text-on-surface"}`}>
                          {isConseil && <Icon name="star" style={{ fontSize: 14 }} className="text-tertiary flex-shrink-0" />}
                          {s.marche}
                        </span>
                        <span className="text-right pl-md text-secondary">{pct(s.proba)}</span>
                        <span className="text-right pl-md text-on-surface-variant">{s.cote.toFixed(2)}</span>
                        <span className={`text-right pl-md font-bold ${s.value >= 0 ? "text-primary" : "text-error"}`}>
                          {s.value >= 0 ? "+" : ""}{Math.round(s.value * 100)}%
                        </span>
                        <button
                          onClick={() => inPicks
                            ? remove(m.fixture_id, s.cle)
                            : add({ match: m.match, ligue: m.ligue, marche: s.marche, cote: s.cote, proba: s.proba, fixture_id: m.fixture_id, cle: s.cle, match_date: m.date ?? "" })
                          }
                          title={inPicks ? "Retirer" : "Ajouter au ticket"}
                          className={`ml-sm w-6 h-6 rounded flex items-center justify-center transition-all flex-shrink-0 ${inPicks ? "bg-primary text-on-primary" : "bg-white/10 hover:bg-primary/30 text-on-surface-variant"}`}
                        >
                          <Icon name={inPicks ? "check" : "add"} style={{ fontSize: 14 }} />
                        </button>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="text-on-surface-variant font-body-md">
                  Cotes indisponibles pour ce match (probabilités calculées affichées dans le 1X2).
                </p>
              )}
            </div>
          </div>

          {/* Classement — tabs par groupe */}
          {m.classement?.groupes && m.classement.groupes.length > 0 && (
            <div className="glass-card rounded-xl p-lg mt-lg">
              <h2 className="font-headline-sm text-headline-sm text-on-surface mb-md flex items-center gap-sm">
                <Icon name="leaderboard" className="text-tertiary" /> Classement — {m.ligue}
              </h2>

              {/* Tabs */}
              {m.classement.groupes.length > 1 && (
                <div className="flex gap-xs flex-wrap mb-md">
                  {m.classement.groupes.map((g, gi) => (
                    <button
                      key={gi}
                      onClick={() => setTabClassement(gi)}
                      className={`px-md py-xs rounded-full font-label-sm text-label-sm transition-all border ${
                        tabClassement === gi
                          ? "bg-tertiary/20 text-tertiary border-tertiary/30"
                          : "bg-white/5 text-on-surface-variant border-white/10 hover:border-tertiary/20"
                      }`}
                    >
                      {g.nom}
                    </button>
                  ))}
                </div>
              )}

              {/* Table du groupe actif, hauteur fixe + scroll */}
              <div className="overflow-x-auto overflow-y-auto max-h-80">
                <GroupeTable
                  lignes={m.classement.groupes[tabClassement]?.lignes ?? []}
                  homeId={m.classement.home_id}
                  awayId={m.classement.away_id}
                />
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

          {/* Derniers matchs */}
          {(m.derniers_matchs_dom?.length > 0 || m.derniers_matchs_ext?.length > 0) && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-lg mt-lg">
              {[
                { equipe: m.home.name, matchs: m.derniers_matchs_dom },
                { equipe: m.away.name, matchs: m.derniers_matchs_ext },
              ].map(({ equipe, matchs }) => (
                <div key={equipe} className="glass-card rounded-xl p-lg">
                  <h2 className="font-headline-sm text-headline-sm text-on-surface mb-md flex items-center gap-sm">
                    <Icon name="history" className="text-secondary" /> {equipe}
                  </h2>
                  <div className="flex flex-col gap-xs">
                    {matchs.map((dm, i) => (
                      <DernierMatchLigne key={i} dm={dm} />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Compositions */}
          {m.compos?.length > 0 ? (
            <div className="glass-card rounded-xl p-lg mt-lg">
              <h2 className="font-headline-sm text-headline-sm text-on-surface mb-md flex items-center gap-sm">
                <Icon name="groups" className="text-secondary" /> Compositions
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-lg">
                {m.compos.map((c) => <CompoCard key={c.equipe} c={c} />)}
              </div>
            </div>
          ) : (
            <div className="glass-card rounded-xl p-lg mt-lg">
              <h2 className="font-headline-sm text-headline-sm text-on-surface mb-md flex items-center gap-sm">
                <Icon name="groups" className="text-secondary" /> Compositions
              </h2>
              <p className="text-on-surface-variant font-body-md">
                Pas encore disponibles — les compositions sont annoncées environ 1h avant le match.
              </p>
            </div>
          )}
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

const RES_COLOR: Record<string, string> = {
  W: "bg-primary/25 text-primary",
  D: "bg-tertiary/25 text-tertiary",
  L: "bg-error/25 text-error",
};
const RES_LABEL: Record<string, string> = { W: "V", D: "N", L: "D" };

function DernierMatchLigne({ dm }: { dm: DernierMatch }) {
  return (
    <div className="flex items-center justify-between gap-sm py-xs border-b border-white/5 last:border-0">
      <span className={`w-6 h-6 rounded flex items-center justify-center font-label-sm text-label-sm font-bold flex-shrink-0 ${RES_COLOR[dm.resultat]}`}>
        {RES_LABEL[dm.resultat]}
      </span>
      <div className="flex flex-col flex-1 min-w-0">
        <span className="font-body-sm text-body-sm text-on-surface truncate">
          {dm.domicile} <span className="text-on-surface-variant">–</span> {dm.exterieur}
        </span>
        <span className="font-label-sm text-label-sm text-on-surface-variant">
          {dateHeureCanada(dm.date)}
        </span>
      </div>
      <span className="font-mono font-bold text-on-surface font-label-md text-label-md flex-shrink-0">
        {dm.score}
      </span>
    </div>
  );
}

const POSTE_ORDER: Record<string, number> = { G: 0, D: 1, M: 2, F: 3 };

function CompoCard({ c }: { c: CompoEquipe }) {
  const titulaires = [...c.titulaires].sort(
    (a, b) => (POSTE_ORDER[a.poste ?? ""] ?? 9) - (POSTE_ORDER[b.poste ?? ""] ?? 9)
  );
  return (
    <div>
      <div className="flex items-center gap-sm mb-sm">
        {c.logo && <img src={c.logo} alt="" className="w-6 h-6 object-contain" />}
        <span className="font-headline-sm text-headline-sm text-on-surface">{c.equipe}</span>
        {c.formation && (
          <span className="ml-auto font-mono font-bold text-primary bg-primary/10 px-sm py-xs rounded">
            {c.formation}
          </span>
        )}
      </div>
      <div className="flex flex-col gap-xs mb-sm">
        {titulaires.map((j, i) => (
          <div key={i} className="flex items-center gap-sm py-xs border-b border-white/5 last:border-0">
            <span className="font-mono text-on-surface-variant w-6 text-right flex-shrink-0">{j.numero ?? "—"}</span>
            <span className="font-body-sm text-body-sm text-on-surface flex-1">{j.nom}</span>
            <span className="font-label-sm text-label-sm text-secondary flex-shrink-0">{j.poste}</span>
          </div>
        ))}
      </div>
      {c.remplacants.length > 0 && (
        <details className="mt-xs">
          <summary className="font-label-sm text-label-sm text-on-surface-variant cursor-pointer">
            Remplaçants ({c.remplacants.length})
          </summary>
          <div className="flex flex-col gap-xs mt-xs">
            {c.remplacants.map((j, i) => (
              <div key={i} className="flex items-center gap-sm py-xs border-b border-white/5 last:border-0">
                <span className="font-mono text-on-surface-variant w-6 text-right flex-shrink-0">{j.numero ?? "—"}</span>
                <span className="font-body-sm text-body-sm text-on-surface-variant flex-1">{j.nom}</span>
                <span className="font-label-sm text-label-sm text-secondary flex-shrink-0">{j.poste}</span>
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}
