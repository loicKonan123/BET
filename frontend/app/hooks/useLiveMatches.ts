"use client";
import { useState, useEffect } from "react";
import { getLiveMatches, LiveMatch } from "../lib/api";

export function useLiveMatches(intervalMs = 60_000) {
  const [matches, setMatches] = useState<LiveMatch[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    const poll = async () => {
      try {
        const data = await getLiveMatches();
        if (active) setMatches(data);
      } catch {
        if (active) setMatches([]);
      } finally {
        if (active) setLoading(false);
      }
    };

    poll();
    const interval = setInterval(poll, intervalMs);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [intervalMs]);

  return { matches, loading };
}
