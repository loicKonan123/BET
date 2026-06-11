"use client";
import { useState, useEffect, useCallback } from "react";
import { getLiveScore, LiveScore } from "../lib/api";

export const LIVE_STATUSES = new Set(["1H", "2H", "HT", "ET", "BT", "P", "INT", "LIVE"]);

export function useLiveScore(fixtureId: number, initialStatus?: string) {
  const [data, setData] = useState<LiveScore | null>(null);
  const [lastPoll, setLastPoll] = useState<Date | null>(null);

  const shouldStart = initialStatus ? LIVE_STATUSES.has(initialStatus) : false;
  const isLive = data ? LIVE_STATUSES.has(data.status) : shouldStart;

  const poll = useCallback(async () => {
    try {
      const score = await getLiveScore(fixtureId);
      setData(score);
      setLastPoll(new Date());
    } catch {}
  }, [fixtureId]);

  useEffect(() => {
    if (!shouldStart) return;
    poll();
    const interval = setInterval(() => {
      // Arrête le polling quand le match est terminé
      if (data && !LIVE_STATUSES.has(data.status)) return;
      poll();
    }, 60_000);
    return () => clearInterval(interval);
  }, [shouldStart, poll]);

  return { liveScore: data, lastPoll, isLive };
}
