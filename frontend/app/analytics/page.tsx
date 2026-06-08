"use client";

import { useEffect, useState } from "react";
import Icon from "../components/Icon";
import { Analytics, getAnalytics } from "../lib/api";

export default function AnalyticsPage() {
  const [a, setA] = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getAnalytics()
      .then(setA)
      .finally(() => setLoading(false));
  }, []);

  return (
    <>
      <div className="mb-xl">
        <h1 className="font-headline-lg text-headline-lg text-primary mb-xs">
          Performance des pronostics
        </h1>
        <p className="font-body-lg text-on-surface-variant">
          Précision du modèle statistique sur les tickets enregistrés.
        </p>
      </div>

      {loading && (
        <div className="flex justify-center py-xl">
          <div className="w-10 h-10 border-4 border-primary border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {a && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-lg mb-lg">
            <Kpi
              label="Taux de réussite"
              value={`${(a.taux_reussite * 100).toFixed(1)}%`}
              icon="target"
              color="primary"
              big
            />
            <Kpi
              label="Tickets gagnés"
              value={String(a.gagnes)}
              icon="check_circle"
              color="primary"
              big
            />
            <Kpi
              label="Tickets perdus"
              value={String(a.perdus)}
              icon="cancel"
              color="error"
              big
            />
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 gap-md mb-lg">
            <Kpi label="Total enregistrés" value={String(a.total)} icon="confirmation_number" color="secondary" />
            <Kpi label="En attente" value={String(a.en_attente)} icon="hourglass_empty" color="tertiary" />
            <Kpi label="Réglés" value={String(a.gagnes + a.perdus)} icon="fact_check" color="secondary" />
          </div>

          {a.total === 0 && (
            <p className="text-on-surface-variant mt-lg">
              Aucune donnée encore — génère et sauvegarde des tickets depuis l&apos;onglet Ticket Gen.
            </p>
          )}
        </>
      )}
    </>
  );
}

function Kpi({
  label,
  value,
  icon,
  color,
  big = false,
}: {
  label: string;
  value: string;
  icon: string;
  color: "primary" | "secondary" | "tertiary" | "error";
  big?: boolean;
}) {
  const text = {
    primary: "text-primary",
    secondary: "text-secondary",
    tertiary: "text-tertiary",
    error: "text-error",
  }[color];
  return (
    <div className="glass-card p-lg rounded-xl flex flex-col gap-sm">
      <div className="flex items-center justify-between">
        <span className="font-label-sm text-label-sm uppercase tracking-widest text-on-surface-variant">
          {label}
        </span>
        <Icon name={icon} className={text} />
      </div>
      <span className={`font-mono font-bold ${text} ${big ? "text-headline-lg" : "text-headline-md"}`}>
        {value}
      </span>
    </div>
  );
}
