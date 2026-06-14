"use client";

import { ReactNode, CSSProperties } from "react";
import Icon from "./Icon";

/* Primitives UI partagées — une seule source de vérité pour les cartes,
 * titres de section, pastilles et tuiles de stats. Style « glassmorphism
 * intensifié », aéré/premium. */

type Div = { children: ReactNode; className?: string; style?: CSSProperties };

/** Carte en verre. `interactive` active l'effet de survol (sinon statique). */
export function Card({
  children,
  className = "",
  style,
  interactive = false,
  onClick,
  delay,
}: Div & { interactive?: boolean; onClick?: () => void; delay?: number }) {
  const enter = delay != null ? "card-enter" : "";
  const st = delay != null ? { ...style, animationDelay: `${delay}ms` } : style;
  return (
    <div
      onClick={onClick}
      className={`glass-card ${interactive ? "" : "glass-static"} p-lg ${enter} ${className}`}
      style={st}
    >
      {children}
    </div>
  );
}

/** Titre de section avec icône, espacé et lisible. */
export function SectionTitle({
  icon,
  children,
  right,
}: {
  icon?: string;
  children: ReactNode;
  right?: ReactNode;
}) {
  return (
    <div className="flex items-center justify-between mb-md">
      <div className="flex items-center gap-sm">
        {icon && <Icon name={icon} className="text-primary" style={{ fontSize: 18 }} />}
        <span className="text-xs uppercase tracking-[0.15em] font-semibold text-on-surface-variant">
          {children}
        </span>
      </div>
      {right}
    </div>
  );
}

type Ton = "neutre" | "primary" | "secondary" | "tertiary" | "accent" | "error";

const TONS: Record<Ton, string> = {
  neutre: "bg-white/8 text-on-surface-variant",
  primary: "bg-primary/15 text-primary",
  secondary: "bg-secondary/15 text-secondary",
  tertiary: "bg-tertiary/15 text-tertiary",
  accent: "bg-accent/15 text-accent",
  error: "bg-error/15 text-error",
};

/** Pastille / badge arrondi. */
export function Pill({
  children,
  ton = "neutre",
  className = "",
}: {
  children: ReactNode;
  ton?: Ton;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1 px-sm py-0.5 rounded-full text-[11px] font-semibold uppercase tracking-wider ${TONS[ton]} ${className}`}
    >
      {children}
    </span>
  );
}

/** Tuile de statistique : grande valeur + libellé. */
export function StatTile({
  label,
  value,
  sub,
  ton = "neutre",
}: {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  ton?: Ton;
}) {
  const accent: Record<Ton, string> = {
    neutre: "text-on-surface",
    primary: "text-primary",
    secondary: "text-secondary",
    tertiary: "text-tertiary",
    accent: "text-accent",
    error: "text-error",
  };
  return (
    <div className="bg-white/5 rounded-xl p-md flex flex-col gap-0.5">
      <span className="text-[11px] uppercase tracking-wider text-on-surface-variant/70">{label}</span>
      <span className={`font-mono font-bold text-xl leading-tight ${accent[ton]}`}>{value}</span>
      {sub && <span className="text-[11px] text-on-surface-variant/60">{sub}</span>}
    </div>
  );
}
