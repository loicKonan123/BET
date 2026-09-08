export function coteDisponible(cote: unknown): cote is number {
  return typeof cote === "number" && Number.isFinite(cote) && cote > 1;
}
