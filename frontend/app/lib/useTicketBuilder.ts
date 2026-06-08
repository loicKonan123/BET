"use client";

import { useCallback, useEffect, useState } from "react";
import { Selection } from "./api";

const KEY = "edge_ticket_builder";

export type PickSelection = Selection & {
  fixture_id: number;
  cle: string;
  match_date: string;
};

export function useTicketBuilder() {
  const [picks, setPicks] = useState<PickSelection[]>([]);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(KEY);
      if (raw) setPicks(JSON.parse(raw));
    } catch {}
  }, []);

  const save = (next: PickSelection[]) => {
    setPicks(next);
    try { localStorage.setItem(KEY, JSON.stringify(next)); } catch {}
  };

  const add = useCallback((sel: PickSelection) => {
    setPicks((prev) => {
      // Un seul pari par match
      if (prev.some((p) => p.fixture_id === sel.fixture_id && p.cle === sel.cle)) return prev;
      const next = [...prev, sel];
      try { localStorage.setItem(KEY, JSON.stringify(next)); } catch {}
      return next;
    });
  }, []);

  const remove = useCallback((fixture_id: number, cle: string) => {
    setPicks((prev) => {
      const next = prev.filter((p) => !(p.fixture_id === fixture_id && p.cle === cle));
      try { localStorage.setItem(KEY, JSON.stringify(next)); } catch {}
      return next;
    });
  }, []);

  const clear = useCallback(() => {
    setPicks([]);
    try { localStorage.removeItem(KEY); } catch {}
  }, []);

  const coteTotale = picks.reduce((acc, p) => acc * p.cote, 1);
  const probaReussite = picks.reduce((acc, p) => acc * p.proba, 1);

  return { picks, add, remove, clear, coteTotale, probaReussite };
}
