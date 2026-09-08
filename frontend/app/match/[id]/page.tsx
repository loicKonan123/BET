"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import Icon from "../../components/Icon";
import PitchView from "../../components/PitchView";
import {
  AnalyseIA, DernierMatch, H2HMatch,
  LigneClassement, MatchDetail, MultiModeles, getAnalyseIA, getMatch,
} from "../../lib/api";
import { useLiveScore } from "../../hooks/useLiveScore";
import { dateHeureCanada } from "../../lib/date";
import { useTicketBuilder } from "../../lib/useTicketBuilder";
import { coteDisponible } from "../../lib/cotes";

// ─── utilitaires ──────────────────────────────────────────────
function pct(x: number) { return `${Math.round(x * 100)}%`; }

const RES_COLOR: Record<string, string> = {
  W: "bg-primary/25 text-primary",
  D: "bg-tertiary/25 text-tertiary",
  L: "bg-error/25 text-error",
};
const RES_LABEL: Record<string, string> = { W: "V", D: "N", L: "D" };

// ─── petits composants ────────────────────────────────────────
function Pastilles({ forme }: { forme: string }) {
  return (
    <div className="flex gap-xs">
      {(forme || "-----").split("").map((c, i) => (
        <span key={i} className={`w-6 h-6 rounded flex items-center justify-center font-label-sm text-label-sm font-bold ${RES_COLOR[c] ?? "bg-white/5 text-on-surface-variant"}`}>
          {RES_LABEL[c] ?? "·"}
        </span>
      ))}
    </div>
  );
}

function Equipe({ id, nom, logo }: { id?: number; nom: string; logo?: string }) {
  const inner = (
    <div className="flex flex-col items-center gap-sm flex-1 text-center group">
      {logo
        ? <img src={logo} alt={nom} className="w-14 h-14 object-contain transition-transform group-hover:scale-110" />
        : <div className="w-14 h-14 rounded-full bg-surface-container-highest flex items-center justify-center"><Icon name="shield" className="text-on-surface-variant" /></div>
      }
      <span className="font-body-md text-body-md text-on-surface font-semibold group-hover:text-primary transition-colors">{nom}</span>
    </div>
  );
  if (id) return <Link href={`/team/${id}`} className="flex-1">{inner}</Link>;
  return inner;
}

function MiniStat({ label, value, color }: { label: string; value: string; color: "primary" | "secondary" | "error" | "tertiary" }) {
  const cls = { primary: "text-primary", secondary: "text-secondary", error: "text-error", tertiary: "text-tertiary" }[color];
  return (
    <div className="bg-white/5 rounded-lg p-sm flex flex-col items-center">
      <span className="font-label-sm text-label-sm text-on-surface-variant">{label}</span>
      <span className={`font-mono font-bold text-headline-sm ${cls}`}>{value}</span>
    </div>
  );
}

// Libellés et couleurs des sources de modèle
const SOURCE_META: Record<string, { label: string; icon: string }> = {
  dynamique: { label: "Poisson bivarié dynamique", icon: "trending_up" },
  contextuel: { label: "Contexte : repos et calendrier", icon: "event" },
  xg_simple: { label: "xG récents", icon: "sports_soccer" },
  poisson:   { label: "Poisson / Dixon-Coles", icon: "functions" },
  elo:       { label: "Elo (force globale)",   icon: "military_tech" },
  marche:    { label: "Marché (sans marge)",   icon: "storefront" },
  ml:        { label: "ML (xG, gradient boosting)", icon: "smart_toy" },
};

// Barre 1X2 segmentée. Les 3 issues sont toujours dans l'ordre Dom / Nul / Ext,
// reliées aux couleurs par la légende affichée en haut de la carte.
function BarreProba({ p, fort }: { p: { "1": number; "X": number; "2": number }; fort?: boolean }) {
  const h = fort ? "h-3" : "h-2";
  return (
    <div className={`flex ${h} rounded-full overflow-hidden bg-surface-container-highest`}>
      <div className="bg-primary" style={{ width: `${Math.round(p["1"] * 100)}%` }} />
      <div className="bg-outline" style={{ width: `${Math.round(p["X"] * 100)}%` }} />
      <div className="bg-secondary" style={{ width: `${Math.round(p["2"] * 100)}%` }} />
    </div>
  );
}

function ConsensusCard({ mm, home, away }: { mm: MultiModeles; home: string; away: string }) {
  const cons = mm.consensus.probabilites!;
  const accord = mm.consensus.accord;
  const convergence = accord == null ? { txt: "Convergence non mesurable", cls: "text-on-surface-variant", icon: "info" }
    : accord <= 0.08 ? { txt: "Les modèles sont proches", cls: "text-primary", icon: "check_circle" }
    : accord <= 0.15 ? { txt: "Accord modéré", cls: "text-tertiary", icon: "remove" }
    : { txt: "Les modèles divergent", cls: "text-tertiary", icon: "info" };
  const sources: Array<[string, typeof mm.poisson]> = [
    ["poisson", mm.poisson], ["elo", mm.elo], ["marche", mm.marche], ["ml", mm.ml ?? null],
    ["dynamique", mm.dynamique ?? null], ["contextuel", mm.contextuel ?? null], ["xg_simple", mm.xg_simple ?? null],
  ];
  const nbSources = Object.values(mm.consensus.poids_utilises).filter(w => w > 0).length;

  // Verdict en clair : l'issue la plus probable du consensus
  const issues = [
    { cle: "1" as const, label: `Victoire ${home}`, pct: cons["1"] },
    { cle: "X" as const, label: "Match nul", pct: cons["X"] },
    { cle: "2" as const, label: `Victoire ${away}`, pct: cons["2"] },
  ];
  const verdict = issues.reduce((a, b) => (b.pct > a.pct ? b : a));

  // Petites valeurs Dom/Nul/Ext sous une barre
  const Valeurs = ({ p }: { p: { "1": number; "X": number; "2": number } }) => (
    <div className="flex justify-between mt-1 text-[11px] font-mono">
      <span className="text-primary">{Math.round(p["1"] * 100)}%</span>
      <span className="text-on-surface-variant">{Math.round(p["X"] * 100)}%</span>
      <span className="text-secondary">{Math.round(p["2"] * 100)}%</span>
    </div>
  );

  return (
    <div className="glass-card p-lg flex flex-col gap-lg">
      {/* En-tête */}
      <div className="flex items-center justify-between gap-md flex-wrap">
        <div className="flex items-center gap-sm">
          <Icon name="hub" className="text-primary" style={{ fontSize: 20 }} />
          <span className="text-xs uppercase tracking-[0.15em] font-semibold text-on-surface-variant">
            EDGE · 90 minutes · {nbSources} sources actives
          </span>
        </div>
        <span className={`flex items-center gap-xs text-[11px] font-medium ${convergence.cls}`}>
          <Icon name={convergence.icon} style={{ fontSize: 15 }} />{convergence.txt}
        </span>
      </div>

      {/* Verdict en clair */}
      <div>
        <div className="flex items-baseline justify-between mb-sm">
          <span className="font-headline-sm text-headline-sm text-on-surface">{verdict.label}</span>
          <span className="font-mono font-black text-headline-md text-primary">{Math.round(verdict.pct * 100)}%</span>
        </div>
        <BarreProba p={cons} fort />
        {/* Légende : relie couleurs et issues */}
        <div className="flex justify-between mt-sm text-xs">
          <span className="flex items-center gap-1.5 text-on-surface-variant min-w-0">
            <span className="w-2.5 h-2.5 rounded-full bg-primary flex-shrink-0" />
            <span className="truncate">{home}</span>
            <span className="font-mono text-on-surface">{Math.round(cons["1"] * 100)}%</span>
          </span>
          <span className="flex items-center gap-1.5 text-on-surface-variant">
            <span className="w-2.5 h-2.5 rounded-full bg-outline flex-shrink-0" />
            Nul <span className="font-mono text-on-surface">{Math.round(cons["X"] * 100)}%</span>
          </span>
          <span className="flex items-center gap-1.5 text-on-surface-variant min-w-0 justify-end">
            <span className="font-mono text-on-surface">{Math.round(cons["2"] * 100)}%</span>
            <span className="truncate">{away}</span>
            <span className="w-2.5 h-2.5 rounded-full bg-secondary flex-shrink-0" />
          </span>
        </div>
      </div>

      {/* Détail par modèle */}
      <p className="text-xs text-on-surface-variant">
        {mm.modele_entraine
          ? `Fusion ${mm.validation?.fusion_retenue ? "enrichie retenue" : "de référence conservée"} après validation sur ${mm.validation?.n_test ?? 0} matchs. Confirmation prospective en cours.`
          : "Historique insuffisant pour déployer la fusion entraînée à cette date : moteur de référence actif."}
        {mm.provenance_cotes?.bookmaker && ` Cotes : ${mm.provenance_cotes.bookmaker}.`}
      </p>
      <div className="flex flex-col gap-md pt-md border-t border-white/10">
        <span className="text-[11px] uppercase tracking-wider text-on-surface-variant/60">
          Avis de chaque modèle
        </span>
        {sources.map(([key, p]) => p && (
          <div key={key}>
            <div className="flex items-center justify-between mb-1">
              <span className="flex items-center gap-xs text-sm text-on-surface-variant">
                <Icon name={SOURCE_META[key].icon} style={{ fontSize: 15 }} />
                {SOURCE_META[key].label}
              </span>
              {mm.consensus.poids_utilises[key] != null ? (
                <span className="text-[11px] text-on-surface-variant/60">
                  pèse {Math.round(mm.consensus.poids_utilises[key] * 100)}%
                </span>
              ) : <span className="text-[11px] text-on-surface-variant/60">Comparaison · poids nul</span>}
            </div>
            <BarreProba p={p} />
            <Valeurs p={p} />
          </div>
        ))}
      </div>

      {mm.consensus.diagnostic && (
        <div className="rounded-lg bg-white/5 p-md text-sm text-on-surface-variant space-y-sm">
          <p className="font-semibold text-on-surface">Solidité du consensus</p>
          {accord != null && <p>Écart maximal entre les sources : {(accord * 100).toFixed(1)} points de probabilité, sur les trois issues.</p>}
          {mm.consensus.diagnostic.favori_stable != null && (
            <p>{mm.consensus.diagnostic.favori_stable
              ? "Le favori reste le même lorsqu’on retire une source à la fois."
              : "Le favori change lorsqu’on retire certaines sources : la conclusion est sensible au modèle retenu."}</p>
          )}
          <details>
            <summary className="cursor-pointer">Voir l’influence de chaque source</summary>
            <ul className="mt-sm space-y-xs">
              {Object.entries(mm.consensus.diagnostic.sensibilite).map(([source, test]) => (
                <li key={source}>Sans {SOURCE_META[source]?.label ?? source} : variation maximale de {(test.ecart_max * 100).toFixed(1)} points{test.favori_change ? ", favori différent" : ""}.</li>
              ))}
            </ul>
          </details>
          <p className="text-xs opacity-70">{mm.consensus.diagnostic.note}</p>
        </div>
      )}

      {mm.elo_info && (
        <div className="flex items-center gap-sm text-[11px] text-on-surface-variant/60 pt-sm border-t border-white/10">
          <Icon name="military_tech" style={{ fontSize: 14 }} />
          Force Elo : {home} {mm.elo_info.rating_dom} vs {away} {mm.elo_info.rating_ext}
          {mm.elo_info.terrain_neutre && " · terrain neutre"}
        </div>
      )}
    </div>
  );
}

function DernierMatchLigne({ dm }: { dm: DernierMatch }) {
  return (
    <div className="flex items-center gap-sm py-xs border-b border-white/5 last:border-0">
      <span className={`w-6 h-6 rounded flex items-center justify-center font-label-sm text-label-sm font-bold flex-shrink-0 ${RES_COLOR[dm.resultat]}`}>
        {RES_LABEL[dm.resultat]}
      </span>
      <div className="flex flex-col flex-1 min-w-0">
        <span className="font-body-sm text-body-sm text-on-surface truncate">
          {dm.domicile} <span className="text-on-surface-variant">–</span> {dm.exterieur}
        </span>
        <span className="font-label-sm text-label-sm text-on-surface-variant">{dateHeureCanada(dm.date)}</span>
      </div>
      <span className="font-mono font-bold text-on-surface font-label-md text-label-md flex-shrink-0">{dm.score}</span>
    </div>
  );
}

function H2HLigne({ h, homeId }: { h: H2HMatch; homeId: number }) {
  const domGagne = (parseInt(h.score[0]) > parseInt(h.score[2]));
  const extGagne = (parseInt(h.score[2]) > parseInt(h.score[0]));
  const isHome = h.home_id === homeId;
  const res = domGagne ? (isHome ? "W" : "L") : extGagne ? (isHome ? "L" : "W") : "D";
  return (
    <div className="flex items-center gap-sm py-xs border-b border-white/5 last:border-0">
      <span className={`w-6 h-6 rounded flex items-center justify-center font-label-sm text-label-sm font-bold flex-shrink-0 ${RES_COLOR[res]}`}>
        {RES_LABEL[res]}
      </span>
      <div className="flex flex-col flex-1 min-w-0">
        <span className="font-body-sm text-body-sm text-on-surface truncate">
          {h.domicile} <span className="text-on-surface-variant">–</span> {h.exterieur}
        </span>
        <span className="font-label-sm text-label-sm text-on-surface-variant">{dateHeureCanada(h.date)}</span>
      </div>
      <span className="font-mono font-bold text-on-surface font-label-md flex-shrink-0">{h.score}</span>
    </div>
  );
}

function AnalyseDetaillee({ ia }: { ia: AnalyseIA }) {
  const blocs = [
    { key: "lecture_match", titre: "Lecture du match", icon: "sports_soccer" },
    { key: "duel_tactique", titre: "Les clés du duel", icon: "sports_soccer" },
    { key: "signaux_statistiques", titre: "Ce que disent les modèles", icon: "query_stats" },
    { key: "scenario_alternatif", titre: "Ce qui pourrait faire basculer le match", icon: "alt_route" },
    { key: "marche_value", titre: "Le favori vaut-il sa cote ?", icon: "monitoring" },
    { key: "risques", titre: "Les réserves de l’analyse", icon: "warning" },
    { key: "verdict", titre: "Verdict", icon: "gavel" },
  ] as const;
  const detail = ia.analyse_detaillee;
  const hasDetail = detail && blocs.some((b) => detail[b.key]);

  return (
    <div className="flex flex-col gap-md">
      {ia.analyse && (
        <div className="bg-white/5 border border-white/10 rounded-lg p-md">
          <div className="font-label-sm text-label-sm uppercase tracking-widest text-on-surface-variant mb-xs">
            La lecture EDGE
          </div>
          <p className="font-body-lg text-body-lg text-on-surface leading-relaxed whitespace-pre-line">
            {ia.analyse}
          </p>
        </div>
      )}

      {hasDetail && (
        <article className="flex flex-col gap-lg max-w-prose mx-auto w-full">
          {blocs.map((b) => {
            const texte = detail?.[b.key];
            if (!texte) return null;
            return (
              <section key={b.key} className="border-b border-white/10 pb-lg last:border-0">
                <div className="flex items-center gap-xs font-label-sm text-label-sm uppercase tracking-widest text-on-surface-variant mb-xs">
                  <Icon name={b.icon} style={{ fontSize: 15 }} />
                  {b.titre}
                </div>
                <p className="font-body-md text-body-md text-on-surface leading-relaxed whitespace-pre-line">
                  {texte}
                </p>
              </section>
            );
          })}
        </article>
      )}
    </div>
  );
}

function GroupeTable({ lignes, homeId, awayId }: { lignes: LigneClassement[]; homeId: number; awayId: number }) {
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
          return (
            <tr key={l.equipe_id} className={`border-t border-white/5 ${dom ? "bg-primary/15" : ext ? "bg-secondary/15" : ""}`}>
              <td className="py-sm pr-sm font-mono text-on-surface-variant">{l.rang}</td>
              <td className="py-sm">
                <span className="flex items-center gap-sm">
                  {l.logo && <img src={l.logo} alt="" className="w-5 h-5 object-contain" />}
                  <span className={`font-body-md text-body-md ${dom ? "text-primary font-semibold" : ext ? "text-secondary font-semibold" : "text-on-surface"}`}>{l.equipe}</span>
                </span>
              </td>
              <td className="py-sm px-sm text-center text-on-surface-variant font-mono">{l.joues}</td>
              <td className="py-sm px-sm text-center text-on-surface-variant font-mono hidden sm:table-cell">
                {l.diff != null && l.diff > 0 ? `+${l.diff}` : l.diff}
              </td>
              <td className="py-sm px-sm text-center font-mono font-bold text-on-surface">{l.points}</td>
              <td className="py-sm pl-sm hidden md:table-cell"><Pastilles forme={(l.forme || "").slice(-5)} /></td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

// ─── page principale ──────────────────────────────────────────
type Tab = "analyse" | "compos" | "classement" | "forme";

export default function MatchPage() {
  const params  = useParams();
  const router  = useRouter();
  const id      = Number(params.id);

  const [m, setM]           = useState<MatchDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [erreur, setErreur]   = useState<string | null>(null);
  const [iaSnapshot, setIa]   = useState<AnalyseIA | null>(null);
  const memeVerdict = iaSnapshot?.probabilites_finales && m?.multi_modeles?.consensus.probabilites &&
    (["1", "X", "2"] as const).every(k => iaSnapshot.probabilites_finales?.[k] === m.multi_modeles?.consensus.probabilites?.[k]);
  const ia = iaSnapshot?.prediction_id === m?.prediction_id || memeVerdict ? iaSnapshot : null;
  const [iaLoading, setIaLoading] = useState(false);
  const [iaErreur, setIaErreur]   = useState<string | null>(null);
  const [tabClassement, setTabClassement] = useState(0);
  const [tab, setTab]         = useState<Tab>("analyse");
  const { picks, add, remove } = useTicketBuilder();

  const { liveScore, isLive } = useLiveScore(id, m?.status);
  const fini = ["FT", "AET", "PEN", "AWD", "WO"].includes(m?.status ?? "");

  useEffect(() => {
    if (!id) return;
    getMatch(id)
      .then((d) => {
        if (d.erreur) { setErreur(d.erreur); return; }
        setM(d);
        if (d.classement?.groupes) {
          const homeId = d.home?.id ?? d.classement.home_id;
          const awayId = d.away?.id ?? d.classement.away_id;
          const idx = d.classement.groupes.findIndex((g) => {
            const ids = new Set(g.lignes.map((l) => l.equipe_id));
            return ids.has(homeId) && ids.has(awayId);
          });
          if (idx >= 0) setTabClassement(idx);
        }
        // Auto-switch vers compos si dispo
        if (d.compos?.length > 0) setTab("compos");
      })
      .catch((e) => setErreur(e instanceof Error ? e.message : "Erreur réseau"))
      .finally(() => setLoading(false));
  }, [id]);

  // À l'ouverture du match : on affiche l'analyse IA SI elle est déjà en cache
  // (aucun appel DeepSeek). Sinon le bouton reste pour la lancer à la demande.
  useEffect(() => {
    if (!id) return;
    getAnalyseIA(id, false, true, m?.prediction_id)
      .then((d) => {
        if (!d.cache_absent && !d.erreur) setIa(d);
      })
      .catch(() => { /* silencieux : le bouton prend le relais */ });
  }, [id, m?.prediction_id]);

  async function demanderIA(force = false) {
    setIaLoading(true); setIaErreur(null);
    try {
      const d = await getAnalyseIA(id, force, false, m?.prediction_id);
      if (d.erreur) setIaErreur(d.erreur);
      else if (!d.cache_absent) {
        setM(await getMatch(id));
        setIa(d);
      }
    } catch (e) {
      setIaErreur(e instanceof Error ? e.message : "Erreur réseau");
    } finally {
      setIaLoading(false);
    }
  }

  const TABS: { key: Tab; label: string; icon: string; disabled?: boolean }[] = [
    { key: "analyse",    label: "Analyse",     icon: "insights" },
    { key: "compos",     label: "Compos",       icon: "groups" },
    { key: "classement", label: "Classement",  icon: "leaderboard", disabled: !m?.classement },
    { key: "forme",      label: "Forme & H2H", icon: "history" },
  ];

  return (
    <>
      {/* Retour */}
      <button
        onClick={() => router.back()}
        className="inline-flex items-center gap-xs text-on-surface-variant hover:text-primary font-label-md text-label-md mb-lg transition-colors"
      >
        <Icon name="arrow_back" style={{ fontSize: 18 }} /> Retour
      </button>

      {loading && (
        <div className="flex flex-col items-center justify-center py-xl">
          <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin mb-md" />
          <p className="text-primary font-label-md animate-pulse">ANALYSE EN COURS…</p>
        </div>
      )}
      {erreur && <div className="glass-card border-error/40 text-error p-lg rounded-xl">Erreur : {erreur}</div>}

      {m && (
        <>
          {/* ── En-tête match (toujours visible) ── */}
          <div className="glass-card rounded-xl p-lg md:p-xl mb-sm">
            <div className="flex items-center justify-between mb-md">
              <span className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-widest">
                🏆 {m.ligue} · {dateHeureCanada(m.date)}
              </span>
              {isLive && (
                <span className="flex items-center gap-xs px-sm py-[3px] rounded-full bg-red-500/15 border border-red-500/30">
                  <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                  <span className="text-[11px] font-bold text-red-400 tracking-wider">
                    {liveScore?.status === "HT" ? "MI-TEMPS" : liveScore?.elapsed ? `${liveScore.elapsed}'` : "LIVE"}
                  </span>
                </span>
              )}
              {fini && (
                <span className="flex items-center gap-xs px-sm py-[3px] rounded-full bg-white/10 border border-white/15">
                  <Icon name="check" style={{ fontSize: 14 }} className="text-on-surface-variant" />
                  <span className="text-[11px] font-bold text-on-surface-variant tracking-wider">TERMINÉ</span>
                </span>
              )}
            </div>

            <div className="flex items-center justify-between gap-md">
              <Equipe id={m.home.id} nom={m.home.name} logo={m.home.logo} />
              <div className="flex flex-col items-center gap-xs">
                {isLive && liveScore ? (
                  <>
                    <span className="font-mono text-[2.5rem] leading-none font-black text-on-surface">
                      {liveScore.score.home}
                      <span className="text-on-surface-variant opacity-40 mx-xs">-</span>
                      {liveScore.score.away}
                    </span>
                    <span className="text-[10px] text-on-surface-variant">score en direct</span>
                  </>
                ) : fini && m.score ? (
                  <>
                    <span className="font-mono text-[2.5rem] leading-none font-black text-on-surface">
                      {m.score.domicile}
                      <span className="text-on-surface-variant opacity-40 mx-xs">-</span>
                      {m.score.exterieur}
                    </span>
                    <span className="text-[10px] text-on-surface-variant">score final</span>
                  </>
                ) : (
                  <>
                    <span className="font-mono text-headline-md text-primary font-bold">
                      {m.buts_attendus.domicile} - {m.buts_attendus.exterieur}
                    </span>
                    <span className="font-label-sm text-label-sm text-on-surface-variant">buts attendus</span>
                  </>
                )}
              </div>
              <Equipe id={m.away.id} nom={m.away.name} logo={m.away.logo} />
            </div>

            {/* Événements live */}
            {isLive && liveScore && liveScore.events.filter(e => e.type === "Goal" || e.type === "Card").length > 0 && (
              <div className="mt-md pt-md border-t border-white/8 flex flex-col gap-xs">
                {liveScore.events
                  .filter((e) => e.type === "Goal" || e.type === "Card")
                  .map((e, i) => {
                    const isHome = e.team_id === m.home.id;
                    const icon = e.type === "Goal" ? "⚽" : e.detail === "Yellow Card" ? "🟨" : "🟥";
                    return (
                      <div key={i} className={`flex items-center gap-xs text-xs text-on-surface-variant ${isHome ? "" : "flex-row-reverse text-right"}`}>
                        <span>{icon}</span>
                        <span className="font-mono text-[10px] opacity-60">{e.elapsed}{e.extra ? `+${e.extra}` : ""}'</span>
                        <span className="font-medium">{e.player}</span>
                        {e.type === "Goal" && e.assist && <span className="opacity-50">(p. {e.assist})</span>}
                      </div>
                    );
                  })}
              </div>
            )}
          </div>

          {/* ── Barre d'onglets ── */}
          <div className="flex gap-xs mb-lg bg-surface-container rounded-2xl p-xs overflow-x-auto">
            {TABS.map((t) => (
              <button
                key={t.key}
                onClick={() => !t.disabled && setTab(t.key)}
                disabled={t.disabled}
                className={`flex items-center gap-xs px-md py-sm rounded-xl font-label-md text-label-md transition-all flex-shrink-0 ${
                  tab === t.key
                    ? "bg-secondary-container text-on-secondary-container font-bold shadow-sm"
                    : t.disabled
                    ? "text-on-surface-variant opacity-30 cursor-not-allowed"
                    : "text-on-surface-variant hover:bg-surface-container-high"
                }`}
              >
                <Icon name={t.icon} style={{ fontSize: 16 }} />
                <span>{t.label}</span>
              </button>
            ))}
          </div>

          {/* ══════════════════════════════════════════════
              ONGLET 1 — ANALYSE
          ══════════════════════════════════════════════ */}
          {tab === "analyse" && (
            <div className="flex flex-col gap-lg">
              {/* Conseil */}
              {m.conseil && (
                <div className="glass-card rounded-xl p-lg border-primary/40" style={{ boxShadow: "0 0 25px rgba(78,222,163,0.12)" }}>
                  <div className="flex items-center gap-sm mb-md">
                    <div className="w-10 h-10 rounded-lg bg-primary/15 flex items-center justify-center">
                      <Icon name="lightbulb" className="text-primary" />
                    </div>
                    <div className="flex-1">
                      <div className="font-label-sm text-label-sm uppercase tracking-widest text-on-surface-variant">Bilan du consensus</div>
                      <div className="font-headline-sm text-headline-sm text-on-surface">{m.conseil.marche}</div>
                    </div>
                    {m.conseil.confiance && (
                      <span className={`font-label-sm text-label-sm px-sm py-0.5 rounded-full ${m.conseil.confiance === "élevée" ? "bg-primary/20 text-primary" : m.conseil.confiance === "moyenne" ? "bg-tertiary/20 text-tertiary" : "bg-white/10 text-on-surface-variant"}`}>
                        Confiance {m.conseil.confiance}
                      </span>
                    )}
                  </div>
                  <div className="grid grid-cols-3 gap-sm mb-md">
                    <MiniStat label="Probabilité" value={pct(m.conseil.proba)} color="secondary" />
                    <MiniStat label="Cote" value={m.conseil.cote ? m.conseil.cote.toFixed(2) : "—"} color="primary" />
                    <MiniStat label="Value" value={m.conseil.cote ? `${m.conseil.value >= 0 ? "+" : ""}${Math.round(m.conseil.value * 100)}%` : "—"} color={m.conseil.value >= 0 ? "primary" : "error"} />
                  </div>
                  <p className="font-body-md text-body-md text-on-surface-variant">{m.conseil.raison}</p>
                </div>
              )}

              {/* Probabilités + forme */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-lg">
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
                        <Icon name="home" style={{ fontSize: 16 }} /> Forme dom.
                      </span>
                      <Pastilles forme={m.forme.domicile} />
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="font-label-md text-label-md text-on-surface-variant flex items-center gap-xs">
                        <Icon name="flight" style={{ fontSize: 16 }} /> Forme ext.
                      </span>
                      <Pastilles forme={m.forme.exterieur} />
                    </div>
                  </div>
                </div>

                {/* Marchés */}
                <div className="glass-card rounded-xl p-lg">
                  <h2 className="font-headline-sm text-headline-sm text-on-surface mb-md">Tous les marchés</h2>
                  {m.selections.length > 0 ? (
                    <div className="flex flex-col gap-xs">
                      <div className="grid font-label-sm text-label-sm text-on-surface-variant px-sm pb-xs" style={{ gridTemplateColumns: "1fr auto auto auto auto" }}>
                        <span>Marché</span>
                        <span className="text-right pl-md">Proba</span>
                        <span className="text-right pl-md">Cote</span>
                        <span className="text-right pl-md">Value</span>
                        <span className="pl-sm" />
                      </div>
                      {m.selections.map((s) => {
                        const cote = coteDisponible(s.cote) ? s.cote : null;
                        const value = cote !== null && Number.isFinite(s.value) ? s.value : null;
                        const inPicks = picks.some((p) => p.fixture_id === m.fixture_id && p.cle === s.cle);
                        const isConseil = m.conseil?.marche === s.marche;
                        return (
                          <div key={s.cle}
                            style={{ gridTemplateColumns: "1fr auto auto auto auto" }}
                            className={`grid items-center px-sm py-sm rounded font-label-md text-label-md ${
                              isConseil ? "bg-tertiary/15 border border-tertiary/40" : s.est_value_bet ? "bg-primary/10 border border-primary/20" : "bg-white/5"
                            }`}
                          >
                            <span className={`flex items-center gap-xs ${isConseil ? "text-tertiary font-semibold" : "text-on-surface"}`}>
                              {isConseil && <Icon name="star" style={{ fontSize: 14 }} className="text-tertiary flex-shrink-0" />}
                              {s.marche}
                            </span>
                            <span className="text-right pl-md text-secondary">{pct(s.proba)}</span>
                            <span className="text-right pl-md text-on-surface-variant" title={cote === null ? "Cote indisponible" : undefined}>{cote !== null ? cote.toFixed(2) : "—"}</span>
                            <span className={`text-right pl-md font-bold ${value === null ? "text-on-surface-variant" : value >= 0 ? "text-primary" : "text-error"}`}>
                              {value !== null ? `${value >= 0 ? "+" : ""}${Math.round(value * 100)}%` : "—"}
                            </span>
                            <button
                              disabled={!inPicks && cote === null}
                              title={inPicks ? "Retirer du ticket" : cote === null ? "Cote indisponible" : "Ajouter au ticket"}
                              aria-label={inPicks ? "Retirer du ticket" : cote === null ? "Cote indisponible" : "Ajouter au ticket"}
                              onClick={() => {
                                if (inPicks) remove(m.fixture_id, s.cle);
                                else if (cote !== null) add({ match: m.match, ligue: m.ligue, marche: s.marche, cote, proba: s.proba, fixture_id: m.fixture_id, cle: s.cle, match_date: m.date ?? "" });
                              }}
                              className={`ml-sm w-6 h-6 rounded flex items-center justify-center transition-all flex-shrink-0 disabled:opacity-40 disabled:cursor-not-allowed ${inPicks ? "bg-primary text-on-primary" : "bg-white/10 hover:bg-primary/30 text-on-surface-variant"}`}
                            >
                              <Icon name={inPicks ? "check" : "add"} style={{ fontSize: 14 }} />
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <p className="text-on-surface-variant font-body-md">Cotes indisponibles pour ce match.</p>
                  )}
                </div>
              </div>

              {/* Consensus multi-modèles */}
              {m.multi_modeles?.consensus?.probabilites && (
                <ConsensusCard mm={m.multi_modeles} home={m.home.name} away={m.away.name} />
              )}

              {/* Analyse IA */}
              <div className="glass-card rounded-xl p-lg">
                <div className="flex items-center justify-between gap-md mb-md flex-wrap">
                  <div className="flex items-center gap-sm">
                    <div className="w-10 h-10 rounded-lg bg-secondary-container/30 flex items-center justify-center">
                      <Icon name="neurology" className="text-secondary" />
                    </div>
                    <div>
                      <div className="font-label-sm text-label-sm uppercase tracking-widest text-on-surface-variant">Prédiction IA</div>
                      <div className="font-headline-sm text-headline-sm text-on-surface">Analyse EDGE</div>
                    </div>
                  </div>
                  {!ia ? (
                    <button onClick={() => demanderIA()} disabled={iaLoading}
                      className="flex items-center gap-sm bg-secondary-container text-on-secondary-container font-label-md text-label-md px-lg py-sm rounded-lg hover:opacity-90 transition-all active:scale-95 disabled:opacity-50">
                      {iaLoading
                        ? <><span className="w-4 h-4 border-2 border-on-secondary-container border-t-transparent rounded-full animate-spin" />Analyse en cours…</>
                        : <><Icon name="auto_awesome" style={{ fontSize: 18 }} />Lancer l'analyse</>}
                    </button>
                  ) : (
                    <button onClick={() => demanderIA(true)} disabled={iaLoading}
                      className="flex items-center gap-xs bg-white/5 hover:bg-white/10 text-on-surface-variant font-label-sm text-label-sm px-md py-sm rounded-lg transition-all disabled:opacity-50">
                      <Icon name="refresh" style={{ fontSize: 16 }} className={iaLoading ? "animate-spin" : ""} />
                      Rafraîchir
                    </button>
                  )}
                </div>
                {iaErreur && <p className="text-error font-body-md">Erreur : {iaErreur}</p>}
                {!ia && !iaLoading && !iaErreur && (
                  <p className="font-body-md text-body-md text-on-surface-variant">
                    L’IA explique le verdict EDGE avec les arguments football disponibles : forme, calendrier, confrontations et effectifs. Les probabilités restent celles du moteur commun.
                  </p>
                )}
                {iaLoading && (
                  <div className="flex flex-col gap-sm">
                    <p className="font-body-md text-body-md text-on-surface-variant animate-pulse">Le raisonneur étudie le dossier complet…</p>
                    <div className="h-1 bg-white/5 rounded overflow-hidden"><div className="h-full bg-secondary animate-pulse w-2/3" /></div>
                  </div>
                )}
                {ia && (
                  <div className="flex flex-col gap-lg">

                    {/* Verdict d'équipe (IA + consensus) — résultat principal */}
                    {(ia.probabilites_finales || ia.probabilites_ia) && (() => {
                      const fin = ia.probabilites_finales;
                      const dom = fin ? fin["1"] : (ia.probabilites_ia?.victoire_domicile ?? 0);
                      const nul = fin ? fin["X"] : (ia.probabilites_ia?.nul ?? 0);
                      const ext = fin ? fin["2"] : (ia.probabilites_ia?.victoire_exterieur ?? 0);
                      const conf = ia.confiance_finale ?? ia.confiance;
                      const pred = ia.prediction_equipe ?? ia.prediction;
                      const div = ia.divergence_consensus ?? null;
                      return (
                      <div className="bg-secondary-container/10 border border-secondary/20 rounded-xl p-md">
                        <div className="flex items-center gap-sm mb-md">
                          <Icon name="groups" className="text-secondary" style={{ fontSize: 18 }} />
                          <span className="font-label-sm text-label-sm uppercase tracking-widest text-secondary">
                            {fin ? "Verdict d'équipe (IA + consensus)" : "Probabilités IA"}
                          </span>
                          {conf && (
                            <span className={`ml-auto font-label-sm text-label-sm px-sm py-0.5 rounded-full ${conf === "élevée" ? "bg-primary/20 text-primary" : conf === "moyenne" ? "bg-tertiary/20 text-tertiary" : "bg-white/10 text-on-surface-variant"}`}>
                              Confiance {conf}
                            </span>
                          )}
                        </div>
                        {/* Barre de probabilités */}
                        <div className="flex rounded overflow-hidden h-3 mb-sm">
                          <div className="bg-primary transition-all" style={{ width: `${Math.round(dom * 100)}%` }} />
                          <div className="bg-outline transition-all" style={{ width: `${Math.round(nul * 100)}%` }} />
                          <div className="bg-secondary transition-all" style={{ width: `${Math.round(ext * 100)}%` }} />
                        </div>
                        <div className="flex justify-between font-label-md text-label-md">
                          <span className="text-primary">Dom. {Math.round(dom * 100)}%</span>
                          <span className="text-on-surface-variant">Nul {Math.round(nul * 100)}%</span>
                          <span className="text-secondary">Ext. {Math.round(ext * 100)}%</span>
                        </div>
                        {pred && (
                          <div className="mt-md pt-md border-t border-white/10 flex items-center gap-sm">
                            <Icon name="emoji_events" className="text-tertiary" style={{ fontSize: 18 }} />
                            <span className="font-body-lg text-body-lg text-on-surface font-semibold">Prédiction : {pred}</span>
                          </div>
                        )}
                        {/* Avis brut de l'IA + écart avec l'équipe (transparence) */}
                        {fin && ia.probabilites_ia && (
                          <div className="mt-sm flex flex-wrap items-center gap-x-md gap-y-xs font-label-sm text-label-sm text-on-surface-variant/70">
                            <span>
                              Avis IA seul : {Math.round((ia.probabilites_ia.victoire_domicile ?? 0) * 100)}% / {Math.round((ia.probabilites_ia.nul ?? 0) * 100)}% / {Math.round((ia.probabilites_ia.victoire_exterieur ?? 0) * 100)}%
                            </span>
                            {div != null && div >= 0.15 && (
                              <span className="flex items-center gap-xs text-tertiary">
                                <Icon name="info" style={{ fontSize: 14 }} />
                                Écart notable avec le consensus ({Math.round(div * 100)} pts) — verdict pondéré
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                      );
                    })()}

                    {/* Analyse narrative */}
                    <AnalyseDetaillee ia={ia} />

                    {/* Points clés */}
                    {ia.points_cles?.length > 0 && (
                      <div>
                        <div className="font-label-sm text-label-sm uppercase tracking-widest text-on-surface-variant mb-xs">Points clés</div>
                        <ul className="flex flex-col gap-xs">
                          {ia.points_cles.map((p, i) => (
                            <li key={i} className="flex items-start gap-sm font-body-md text-body-md text-on-surface">
                              <Icon name="check_circle" className="text-primary mt-0.5" style={{ fontSize: 16 }} />{p}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Facteurs correctifs vs Poisson */}
                    {((ia.facteurs_correctifs_vs_poisson?.length ?? 0) > 0 || ((ia.facteurs_risque ?? []).length > 0)) && (
                      <div>
                        <div className="font-label-sm text-label-sm uppercase tracking-widest text-on-surface-variant mb-xs">Corrections vs modèle statistique</div>
                        <ul className="flex flex-col gap-xs">
                          {(ia.facteurs_correctifs_vs_poisson?.length ? ia.facteurs_correctifs_vs_poisson : (ia.facteurs_risque ?? [])).map((p, i) => (
                            <li key={i} className="flex items-start gap-sm font-body-md text-body-md text-on-surface">
                              <Icon name="tune" className="text-tertiary mt-0.5" style={{ fontSize: 16 }} />{p}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Recommandation */}
                    {ia.recommandation && (
                      <div className="bg-secondary-container/20 border border-secondary/20 rounded-lg p-md">
                        <div className="flex items-center justify-between mb-xs flex-wrap gap-xs">
                          <span className="font-headline-sm text-headline-sm text-secondary">{ia.recommandation.marche}</span>
                          <span className={`font-label-sm text-label-sm uppercase tracking-widest px-sm py-0.5 rounded-full ${ia.recommandation.confiance === "élevée" ? "bg-primary/20 text-primary" : "bg-white/10 text-on-surface-variant"}`}>
                            Confiance {ia.recommandation.confiance}
                          </span>
                        </div>
                        <p className="font-body-md text-body-md text-on-surface-variant">{ia.recommandation.justification}</p>
                      </div>
                    )}

                    {/* Référence Poisson (secondaire) */}
                    {m?.probabilites && (
                      <div className="border-t border-white/10 pt-md">
                        <div className="font-label-sm text-label-sm uppercase tracking-widest text-on-surface-variant/60 mb-xs">Verdict du moteur EDGE</div>
                        <div className="flex gap-md font-body-sm text-body-sm text-on-surface-variant/60">
                          <span>Dom. {pct(m.probabilites["1"] ?? 0)}</span>
                          <span>Nul {pct(m.probabilites["X"] ?? 0)}</span>
                          <span>Ext. {pct(m.probabilites["2"] ?? 0)}</span>
                        </div>
                      </div>
                    )}

                    {ia.cache && <span className="font-label-sm text-label-sm text-on-surface-variant/60 self-end">Depuis le cache</span>}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ══════════════════════════════════════════════
              ONGLET 2 — COMPOSITIONS
          ══════════════════════════════════════════════ */}
          {tab === "compos" && (
            <div className="glass-card rounded-xl p-lg">
              {m.compos?.length > 0
                ? <PitchView compos={m.compos} />
                : (
                  <div className="flex flex-col items-center py-xl text-center">
                    <Icon name="groups" style={{ fontSize: 48, opacity: 0.2 }} />
                    <p className="mt-md text-on-surface-variant font-body-md">
                      Compositions pas encore disponibles.
                    </p>
                    <p className="text-on-surface-variant/60 font-label-sm text-label-sm mt-xs">
                      Annoncées environ 1h avant le coup d'envoi.
                    </p>
                  </div>
                )}
            </div>
          )}

          {/* ══════════════════════════════════════════════
              ONGLET 3 — CLASSEMENT
          ══════════════════════════════════════════════ */}
          {tab === "classement" && m.classement?.groupes && (
            <div className="glass-card rounded-xl p-lg">
              <h2 className="font-headline-sm text-headline-sm text-on-surface mb-md flex items-center gap-sm">
                <Icon name="leaderboard" className="text-tertiary" /> {m.ligue}
              </h2>
              {m.classement.groupes.length > 1 && (
                <div className="flex gap-xs flex-wrap mb-md">
                  {m.classement.groupes.map((g, gi) => (
                    <button key={gi} onClick={() => setTabClassement(gi)}
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
              <div className="overflow-x-auto overflow-y-auto max-h-[600px]">
                <GroupeTable lignes={m.classement.groupes[tabClassement]?.lignes ?? []} homeId={m.classement.home_id} awayId={m.classement.away_id} />
              </div>
              <div className="flex gap-lg mt-md font-label-sm text-label-sm">
                <span className="flex items-center gap-xs text-on-surface-variant"><span className="w-3 h-3 rounded bg-primary/40" /> {m.home.name}</span>
                <span className="flex items-center gap-xs text-on-surface-variant"><span className="w-3 h-3 rounded bg-secondary/40" /> {m.away.name}</span>
              </div>
            </div>
          )}

          {/* ══════════════════════════════════════════════
              ONGLET 4 — FORME & H2H
          ══════════════════════════════════════════════ */}
          {tab === "forme" && (
            <div className="flex flex-col gap-lg">
              {/* Derniers matchs */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-lg">
                {[
                  { equipe: m.home.name, logo: m.home.logo, matchs: m.derniers_matchs_dom },
                  { equipe: m.away.name, logo: m.away.logo, matchs: m.derniers_matchs_ext },
                ].map(({ equipe, logo, matchs }) => (
                  <div key={equipe} className="glass-card rounded-xl p-lg">
                    <h2 className="font-headline-sm text-headline-sm text-on-surface mb-md flex items-center gap-sm">
                      {logo && <img src={logo} alt="" className="w-5 h-5 object-contain" />}
                      {equipe}
                    </h2>
                    {matchs?.length > 0
                      ? <div className="flex flex-col gap-xs">{matchs.map((dm, i) => <DernierMatchLigne key={i} dm={dm} />)}</div>
                      : <p className="text-on-surface-variant font-body-sm">Pas de données disponibles.</p>
                    }
                  </div>
                ))}
              </div>

              {/* H2H */}
              {m.h2h?.length > 0 && (
                <div className="glass-card rounded-xl p-lg">
                  <h2 className="font-headline-sm text-headline-sm text-on-surface mb-md flex items-center gap-sm">
                    <Icon name="compare_arrows" className="text-secondary" />
                    Confrontations directes
                    <span className="font-label-sm text-label-sm text-on-surface-variant opacity-60 ml-auto">{m.home.name} vs {m.away.name}</span>
                  </h2>
                  <div className="flex flex-col gap-xs">
                    {m.h2h.map((h, i) => <H2HLigne key={i} h={h} homeId={m.home.id} />)}
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </>
  );
}
