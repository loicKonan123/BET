"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import Icon from "./components/Icon";
import { Analytics, getAnalytics } from "./lib/api";

export default function Home() {
  const [a, setA] = useState<Analytics | null>(null);

  useEffect(() => {
    getAnalytics().then(setA).catch(() => {});
  }, []);

  return (
    <>
      {/* HERO */}
      <section className="relative overflow-hidden glass-card rounded-xl px-lg md:px-xl py-xl mb-xl">
        {/* halo */}
        <div className="absolute -top-24 -right-24 w-80 h-80 rounded-full bg-primary/10 blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 w-80 h-80 rounded-full bg-secondary-container/10 blur-3xl pointer-events-none" />

        <div className="relative max-w-3xl">
          <div className="inline-flex items-center gap-sm bg-primary/10 border border-primary/20 rounded-full px-md py-xs mb-lg">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-primary" />
            </span>
            <span className="font-label-sm text-label-sm uppercase tracking-widest text-primary">
              Moteur statistique actif
            </span>
          </div>

          <h1 className="font-display-lg text-display-lg font-black tracking-tighter mb-md">
            <span className="text-primary">EDGE</span>
            <span className="text-on-surface"> — Find the Value</span>
          </h1>

          <p className="font-body-lg text-on-surface-variant max-w-2xl mb-xl">
            Ton avantage statistique sur le bookmaker. EDGE scanne automatiquement
            les matchs jouables sur Mise-o-jeu, calcule les probabilités par loi de
            Poisson et génère les combinés à plus forte value. Zéro intuition, que
            des maths.
          </p>

          <div className="flex flex-col sm:flex-row gap-md">
            <Link
              href="/generate"
              className="flex items-center justify-center gap-sm bg-primary text-on-primary font-headline-sm text-headline-sm px-xl py-md rounded-xl hover:shadow-[0_0_25px_rgba(78,222,163,0.35)] transition-all active:scale-95 group"
            >
              <Icon name="bolt" className="group-hover:animate-pulse" />
              Générer mes tickets
            </Link>
            <Link
              href="/analytics"
              className="flex items-center justify-center gap-sm bg-white/5 hover:bg-white/10 border border-white/10 text-on-surface font-label-md text-label-md px-xl py-md rounded-xl transition-all"
            >
              <Icon name="analytics" />
              Voir mes performances
            </Link>
          </div>
        </div>
      </section>

      {/* SNAPSHOT LIVE */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-md mb-xl">
        <Snap
          label="ROI"
          value={a ? `${a.roi >= 0 ? "+" : ""}${(a.roi * 100).toFixed(1)}%` : "—"}
          icon="trending_up"
          color={a && a.roi < 0 ? "error" : "primary"}
        />
        <Snap
          label="Taux de réussite"
          value={a ? `${(a.taux_reussite * 100).toFixed(0)}%` : "—"}
          icon="target"
          color="secondary"
        />
        <Snap
          label="Profit net"
          value={a ? `${a.profit >= 0 ? "+" : ""}${a.profit.toFixed(0)}$` : "—"}
          icon="payments"
          color={a && a.profit < 0 ? "error" : "primary"}
        />
        <Snap
          label="Tickets joués"
          value={a ? String(a.gagnes + a.perdus) : "—"}
          icon="confirmation_number"
          color="tertiary"
        />
      </div>

      {/* COMMENT ÇA MARCHE */}
      <h2 className="font-headline-sm text-headline-sm text-on-surface mb-md flex items-center gap-sm">
        <Icon name="insights" className="text-tertiary" />
        Comment EDGE trouve la value
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-lg">
        <Feature
          icon="functions"
          titre="100 % statistique"
          texte="Loi de Poisson sur les buts attendus : probabilité de chaque résultat (1X2, Over/Under, BTTS, double chance). Transparent et auditable, sans boîte noire."
        />
        <Feature
          icon="verified"
          titre="Jouable sur Mise-o-jeu"
          texte="Un validateur ne garde que les championnats réellement offerts par Mise-o-jeu. Chaque ticket généré est jouable chez Loto-Québec."
        />
        <Feature
          icon="query_stats"
          titre="Value & suivi ROI"
          texte="On ne garde que les paris où notre probabilité dépasse la cote. Sauvegarde tes tickets, marque-les gagnés/perdus, suis ton ROI réel."
        />
      </div>

      <p className="font-label-sm text-label-sm text-on-surface-variant mt-xl">
        ⚠️ Les paris sportifs comportent des risques. EDGE fournit des probabilités,
        pas des certitudes. Jouez de manière responsable.
      </p>
    </>
  );
}

function Snap({
  label,
  value,
  icon,
  color,
}: {
  label: string;
  value: string;
  icon: string;
  color: "primary" | "secondary" | "tertiary" | "error";
}) {
  const text = {
    primary: "text-primary",
    secondary: "text-secondary",
    tertiary: "text-tertiary",
    error: "text-error",
  }[color];
  return (
    <div className="glass-card p-md rounded-lg flex flex-col gap-xs">
      <div className="flex items-center justify-between">
        <span className="font-label-sm text-label-sm uppercase tracking-widest text-on-surface-variant">
          {label}
        </span>
        <Icon name={icon} className={text} style={{ fontSize: 18 }} />
      </div>
      <span className={`font-mono font-bold text-headline-md ${text}`}>{value}</span>
    </div>
  );
}

function Feature({
  icon,
  titre,
  texte,
}: {
  icon: string;
  titre: string;
  texte: string;
}) {
  return (
    <div className="glass-card p-lg rounded-xl">
      <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center mb-md">
        <Icon name={icon} className="text-primary" />
      </div>
      <h3 className="font-headline-sm text-headline-sm text-on-surface mb-xs">
        {titre}
      </h3>
      <p className="font-body-md text-body-md text-on-surface-variant">{texte}</p>
    </div>
  );
}
