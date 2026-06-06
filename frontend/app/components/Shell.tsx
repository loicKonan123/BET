"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import Icon from "./Icon";

const NAV = [
  { href: "/", label: "Accueil", icon: "home" },
  { href: "/generate", label: "Générer", icon: "bolt" },
  { href: "/analyses", label: "Analyses", icon: "insights" },
  { href: "/analytics", label: "Performance", icon: "analytics" },
  { href: "/history", label: "Historique", icon: "history" },
];

const NAV_BIENTOT = [
  { label: "Markets", icon: "query_stats" },
  { label: "Live Betting", icon: "sensors" },
];

export default function Shell({ children }: { children: React.ReactNode }) {
  const path = usePathname();

  return (
    <>
      {/* Barre supérieure */}
      <header className="fixed top-0 w-full z-50 bg-surface/60 backdrop-blur-xl border-b border-white/10 flex justify-between items-center px-margin-mobile md:px-margin-desktop h-16">
        <div className="flex items-center gap-md">
          <Link
            href="/"
            className="font-display-lg text-headline-lg font-black tracking-tighter text-primary"
          >
            EDGE
          </Link>
        </div>
        <div className="flex items-center gap-sm">
          <span className="hidden sm:inline font-label-sm text-label-sm text-on-surface-variant mr-sm">
            Conseils de paris · pas de mise ici
          </span>
          <button className="material-symbols-outlined p-sm rounded-full hover:bg-primary/10 text-on-surface-variant transition-colors active:scale-95">
            notifications
          </button>
          <button className="material-symbols-outlined p-sm rounded-full hover:bg-primary/10 text-on-surface-variant transition-colors active:scale-95">
            account_circle
          </button>
        </div>
      </header>

      {/* Sidebar desktop */}
      <aside className="fixed left-0 top-16 h-[calc(100vh-64px)] w-64 hidden md:flex flex-col py-lg px-md gap-sm bg-surface-container-lowest/80 backdrop-blur-2xl border-r border-white/10">
        <nav className="flex-1 flex flex-col gap-xs">
          {NAV_BIENTOT.map((it) => (
            <span
              key={it.label}
              title="Bientôt"
              className="flex items-center gap-md p-md text-on-surface-variant/40 rounded-lg cursor-not-allowed select-none"
            >
              <Icon name={it.icon} />
              <span className="font-label-md text-label-md">{it.label}</span>
            </span>
          ))}
          {NAV.map((it) => {
            const actif = path === it.href;
            return (
              <Link
                key={it.href}
                href={it.href}
                className={
                  actif
                    ? "flex items-center gap-md p-md bg-secondary-container text-on-secondary-container rounded-lg font-bold"
                    : "flex items-center gap-md p-md text-on-surface-variant hover:bg-surface-container-high transition-all hover:translate-x-1 rounded-lg"
                }
              >
                <Icon name={it.icon} />
                <span className="font-label-md text-label-md">{it.label}</span>
              </Link>
            );
          })}
        </nav>
        <div className="mt-auto flex flex-col gap-xs border-t border-white/5 pt-md">
          <span className="flex items-center gap-md px-md py-sm text-on-surface-variant/60">
            <Icon name="settings" />
            <span className="font-label-md text-label-md">Réglages</span>
          </span>
          <span className="flex items-center gap-md px-md py-sm text-on-surface-variant/60">
            <Icon name="help_center" />
            <span className="font-label-md text-label-md">Aide</span>
          </span>
        </div>
      </aside>

      {/* Contenu */}
      <main className="pt-24 pb-24 md:ml-64 px-margin-mobile md:px-xl min-h-screen">
        {children}
      </main>

      {/* Nav mobile */}
      <nav className="fixed bottom-0 w-full z-50 md:hidden bg-surface-container-high/90 backdrop-blur-md border-t border-white/10 flex justify-around items-center h-16">
        {NAV.map((it) => {
          const actif = path === it.href;
          return (
            <Link
              key={it.href}
              href={it.href}
              className={`flex flex-col items-center p-xs rounded transition-all ${
                actif ? "text-primary scale-110" : "text-on-surface-variant"
              }`}
            >
              <Icon name={it.icon} />
              <span className="font-label-sm text-label-sm">{it.label}</span>
            </Link>
          );
        })}
      </nav>
    </>
  );
}
