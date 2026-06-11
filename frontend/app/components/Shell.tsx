"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTicketBuilder } from "../lib/useTicketBuilder";
import Icon from "./Icon";
import LiveWidget from "./LiveWidget";
import ThemeToggle from "./ThemeToggle";

const NAV = [
  { href: "/", label: "Accueil", icon: "home" },
  { href: "/scores", label: "Scores", icon: "scoreboard" },
  { href: "/generate", label: "Générer", icon: "bolt" },
  { href: "/analyses", label: "Analyses", icon: "insights" },
  { href: "/backtest", label: "Backtest", icon: "science" },
  { href: "/analytics", label: "Performance", icon: "analytics" },
  { href: "/history", label: "Historique", icon: "history" },
];

export default function Shell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const { picks } = useTicketBuilder();

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
          <ThemeToggle />
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

          {/* Live matches */}
          <LiveWidget />

          {/* Ticket builder */}
          <Link
            href="/ticket-builder"
            className={`flex items-center gap-md p-md rounded-lg transition-all ${
              path === "/ticket-builder"
                ? "bg-secondary-container text-on-secondary-container font-bold"
                : "text-on-surface-variant hover:bg-surface-container-high hover:translate-x-1"
            }`}
          >
            <span className="relative">
              <Icon name="receipt_long" />
              {picks.length > 0 && (
                <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-primary text-on-primary flex items-center justify-center font-mono text-[10px] font-bold">
                  {picks.length}
                </span>
              )}
            </span>
            <span className="font-label-md text-label-md">Mon ticket</span>
          </Link>
        </nav>
      </aside>

      {/* Contenu */}
      <main className="pt-24 pb-24 md:ml-64 min-h-screen">
        <div className="max-w-7xl mx-auto px-margin-mobile md:px-xl">
          {children}
        </div>
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
        <Link
          href="/ticket-builder"
          className={`flex flex-col items-center p-xs rounded transition-all relative ${
            path === "/ticket-builder" ? "text-primary scale-110" : "text-on-surface-variant"
          }`}
        >
          <span className="relative">
            <Icon name="receipt_long" />
            {picks.length > 0 && (
              <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-primary text-on-primary flex items-center justify-center font-mono text-[10px] font-bold">
                {picks.length}
              </span>
            )}
          </span>
          <span className="font-label-sm text-label-sm">Ticket</span>
        </Link>
      </nav>
    </>
  );
}
