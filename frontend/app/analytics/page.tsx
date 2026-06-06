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
          Analytics
        </h1>
        <p className="font-body-lg text-on-surface-variant">
          Performance de tes tickets sauvegardés (basée sur les résultats marqués).
        </p>
      </div>

      {loading && (
        <div className="flex justify-center py-xl">
          <div className="w-10 h-10 border-4 border-primary border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {a && (
        <>
          {/* KPIs principaux */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-lg mb-lg">
            <Kpi
              label="ROI"
              value={`${a.roi >= 0 ? "+" : ""}${(a.roi * 100).toFixed(1)}%`}
              icon="trending_up"
              color={a.roi >= 0 ? "primary" : "error"}
              big
            />
            <Kpi
              label="Taux de réussite"
              value={`${(a.taux_reussite * 100).toFixed(1)}%`}
              icon="target"
              color="secondary"
              big
            />
            <Kpi
              label="Profit net"
              value={`${a.profit >= 0 ? "+" : ""}${a.profit.toFixed(2)}$`}
              icon="payments"
              color={a.profit >= 0 ? "primary" : "error"}
              big
            />
          </div>

          {/* Détails */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-md mb-lg">
            <Kpi label="Tickets" value={String(a.total)} icon="confirmation_number" color="secondary" />
            <Kpi label="Gagnés" value={String(a.gagnes)} icon="check_circle" color="primary" />
            <Kpi label="Perdus" value={String(a.perdus)} icon="cancel" color="error" />
            <Kpi label="En attente" value={String(a.en_attente)} icon="hourglass_empty" color="tertiary" />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-md">
            <Kpi label="Mise totale (réglée)" value={`${a.mise_totale.toFixed(2)}$`} icon="account_balance_wallet" color="secondary" />
            <Kpi label="Gain total" value={`${a.gain_total.toFixed(2)}$`} icon="savings" color="primary" />
          </div>

          {a.total === 0 && (
            <p className="text-on-surface-variant mt-lg">
              Aucune donnée encore — sauvegarde des tickets puis marque-les gagnés/perdus dans l&apos;Historique.
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
