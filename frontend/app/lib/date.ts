// Dates/heures en heure de Montréal, format AM/PM simple.

const TZ = "America/Toronto";

/** Jour civil à Montréal, indépendant du fuseau du navigateur. */
export function dateISOCanada(date: Date = new Date()): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(date);
  const part = (type: string) => parts.find(p => p.type === type)!.value;
  return `${part("year")}-${part("month")}-${part("day")}`;
}

/** Date + heure complète, ex. "dim. 7 juin 2026, 9:00 AM". */
export function dateHeureCanada(iso: string): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-CA", {
    timeZone: TZ,
    weekday: "short",
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
}

/** Date seule, ex. "7 juin 2026". */
export function dateCanada(iso: string): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("fr-CA", {
    timeZone: TZ,
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

/** Heure seule, ex. "9:00 AM". */
export function heureCanada(iso: string): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleTimeString("en-CA", {
    timeZone: TZ,
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
}
