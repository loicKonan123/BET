import Link from "next/link";
import { Analyse } from "../lib/api";
import { dateHeureCanada } from "../lib/date";
import Icon from "./Icon";

const LIVE_STATUTS = new Set(["1H","HT","2H","ET","BT","P","SUSP","INT","LIVE"]);
const FINI_STATUTS = new Set(["FT","AET","PEN","AWD","WO"]);

function StatutBadge({ status, date }: { status?: string; date?: string }) {
  if (LIVE_STATUTS.has(status ?? "")) {
    return (
      <span className="flex items-center gap-xs px-sm py-xs rounded-full bg-error/20 text-error font-label-sm text-label-sm">
        <span className="w-1.5 h-1.5 rounded-full bg-error animate-ping inline-block" />
        En cours
      </span>
    );
  }
  if (FINI_STATUTS.has(status ?? "")) {
    return (
      <span className="flex items-center gap-xs px-sm py-xs rounded-full bg-white/10 text-on-surface-variant font-label-sm text-label-sm">
        <Icon name="check" style={{ fontSize: 13 }} />
        Terminé
      </span>
    );
  }
  return (
    <span className="font-label-sm text-label-sm text-on-surface-variant">
      {date ? dateHeureCanada(date) : "—"}
    </span>
  );
}

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
        <span
          key={i}
          className={`w-5 h-5 rounded flex items-center justify-center font-label-sm text-label-sm font-bold ${
            couleur[c] ?? "bg-white/5 text-on-surface-variant"
          }`}
        >
          {lettre[c] ?? "·"}
        </span>
      ))}
    </div>
  );
}

export default function AnalyseMatch({ a, href }: { a: Analyse; href?: string }) {
  const [dom, ext] = a.match.split(" - ");
  const p1 = a.probabilites?.["1"] ?? 0;
  const pX = a.probabilites?.["X"] ?? 0;
  const p2 = a.probabilites?.["2"] ?? 0;
  const pct = (x: number) => `${Math.round(x * 100)}%`;

  const card = (
    <div className="glass-card p-lg rounded-xl flex flex-col gap-md h-full">
      {/* Entête */}
      <div>
        <div className="flex items-center justify-between mb-xs">
          <span className="font-label-sm text-label-sm text-on-surface-variant">🏆 {a.ligue}</span>
          <StatutBadge status={a.status} date={a.date} />
        </div>
        <div className="flex items-center justify-between gap-sm">
          <span className="font-body-md text-body-md text-on-surface font-semibold flex-1">
            {dom}
          </span>
          {a.score
            ? <span className={`font-mono font-bold text-headline-sm px-sm ${LIVE_STATUTS.has(a.status ?? "") ? "text-error" : "text-on-surface"}`}>
                {a.score.domicile} - {a.score.exterieur}
              </span>
            : <span className="font-label-sm text-label-sm text-on-surface-variant">vs</span>
          }
          <span className="font-body-md text-body-md text-on-surface font-semibold text-right flex-1">
            {ext}
          </span>
        </div>
      </div>

      {/* Barre 1X2 */}
      <div>
        <div className="flex h-2 rounded-full overflow-hidden bg-surface-container-highest">
          <div className="bg-primary" style={{ width: pct(p1) }} />
          <div className="bg-outline" style={{ width: pct(pX) }} />
          <div className="bg-secondary" style={{ width: pct(p2) }} />
        </div>
        <div className="flex justify-between mt-xs font-label-sm text-label-sm">
          <span className="text-primary">Dom. {pct(p1)}</span>
          <span className="text-on-surface-variant">Nul {pct(pX)}</span>
          <span className="text-secondary">Ext. {pct(p2)}</span>
        </div>
      </div>

      {/* Buts attendus */}
      <div className="flex items-center justify-between font-label-md text-label-md">
        <span className="flex items-center gap-xs text-on-surface-variant">
          <Icon name="sports_soccer" style={{ fontSize: 16 }} /> Buts attendus
        </span>
        <span>
          <span className="text-primary font-bold">{a.buts_attendus.domicile}</span>
          <span className="text-on-surface-variant"> - </span>
          <span className="text-secondary font-bold">{a.buts_attendus.exterieur}</span>
        </span>
      </div>

      {/* Forme */}
      <div className="flex flex-col gap-xs pt-sm border-t border-white/10">
        <div className="flex items-center justify-between">
          <span className="font-label-sm text-label-sm text-on-surface-variant flex items-center gap-xs">
            <Icon name="home" style={{ fontSize: 14 }} /> Domicile
          </span>
          <Pastilles forme={a.forme.domicile} />
        </div>
        <div className="flex items-center justify-between">
          <span className="font-label-sm text-label-sm text-on-surface-variant flex items-center gap-xs">
            <Icon name="flight" style={{ fontSize: 14 }} /> Extérieur
          </span>
          <Pastilles forme={a.forme.exterieur} />
        </div>
      </div>

      {href && (
        <div className="flex items-center justify-end gap-xs text-primary font-label-sm text-label-sm pt-xs mt-auto">
          Analyse détaillée
          <Icon name="arrow_forward" style={{ fontSize: 16 }} />
        </div>
      )}
    </div>
  );

  if (href) {
    return (
      <Link href={href} className="block hover:-translate-y-1 transition-transform">
        {card}
      </Link>
    );
  }
  return card;
}
