// Affichage des dates/heures en heure du Canada (Est — Québec/Toronto).
// L'API renvoie les heures en UTC ; on les convertit explicitement.

const TZ = "America/Toronto";

/** Date + heure complète, ex. "jeu. 11 juin 2026, 15:00 HAE". */
export function dateHeureCanada(iso: string): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("fr-CA", {
    timeZone: TZ,
    weekday: "short",
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZoneName: "short",
  });
}

/** Date seule, ex. "11 juin 2026". */
export function dateCanada(iso: string): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("fr-CA", {
    timeZone: TZ,
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

/** Heure seule, ex. "15:00 HAE". */
export function heureCanada(iso: string): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleTimeString("fr-CA", {
    timeZone: TZ,
    hour: "2-digit",
    minute: "2-digit",
    timeZoneName: "short",
  });
}
