"use client";

import { useState, ReactElement } from "react";
import { useRouter } from "next/navigation";
import { CompoEquipe, Joueur } from "../lib/api";

const PHOTO_BASE = "https://media.api-sports.io/football/players";

function parseGrid(grid?: string): { row: number; col: number } {
  if (!grid) return { row: 1, col: 1 };
  const [r, c] = grid.split(":").map(Number);
  return { row: r || 1, col: c || 1 };
}

function PlayerToken({
  joueur,
  x,
  y,
  color,
  uid,
  onPlayerClick,
}: {
  joueur: Joueur;
  x: number;
  y: number;
  color: string;
  uid: string;
  onPlayerClick?: (id: number) => void;
}) {
  const [photoError, setPhotoError] = useState(false);
  const r = 18;
  const nomCourt = joueur.nom.split(" ").pop() ?? joueur.nom;
  const clipId = `clip-${uid}`;
  const url = joueur.id ? `${PHOTO_BASE}/${joueur.id}.png` : null;
  const showPhoto = url && !photoError;

  return (
    <g
      onClick={() => joueur.id && onPlayerClick?.(joueur.id)}
      style={{ cursor: joueur.id && onPlayerClick ? "pointer" : "default" }}
    >
      <defs>
        <clipPath id={clipId}>
          <circle cx={x} cy={y} r={r - 1} />
        </clipPath>
      </defs>

      {/* Ombre */}
      <circle cx={x + 1} cy={y + 2} r={r} fill="rgba(0,0,0,0.3)" />
      {/* Fond coloré */}
      <circle cx={x} cy={y} r={r} fill={color} stroke="white" strokeWidth={2} />

      {/* Photo */}
      {showPhoto && (
        <image
          href={url}
          x={x - r + 1} y={y - r + 1}
          width={(r - 1) * 2} height={(r - 1) * 2}
          clipPath={`url(#${clipId})`}
          preserveAspectRatio="xMidYMid slice"
          onError={() => setPhotoError(true)}
        />
      )}

      {/* Numéro (fallback) */}
      {!showPhoto && (
        <text
          x={x} y={y + 1}
          textAnchor="middle"
          dominantBaseline="middle"
          fill="white"
          fontSize={10}
          fontWeight="700"
          fontFamily="monospace"
        >
          {joueur.numero ?? "?"}
        </text>
      )}

      {/* Nom sous le jeton */}
      <text
        x={x} y={y + r + 10}
        textAnchor="middle"
        fill="white"
        fontSize={8}
        fontWeight="600"
        fontFamily="sans-serif"
        style={{ filter: "drop-shadow(0 1px 2px rgba(0,0,0,0.9))" }}
      >
        {nomCourt.length > 9 ? nomCourt.slice(0, 9) + "." : nomCourt}
      </text>
    </g>
  );
}

/** Rendu d'une équipe dans sa moitié horizontale.
 *  xStart / xEnd = zone x allouée
 *  attackRight : home (gauche → droite), !attackRight : away (droite → gauche)
 */
function TeamHalf({
  equipe,
  couleur,
  xStart,
  xEnd,
  pitchYTop,
  pitchYBot,
  attackRight,
  teamIndex,
  onPlayerClick,
}: {
  equipe: CompoEquipe;
  couleur: string;
  xStart: number;
  xEnd: number;
  pitchYTop: number;
  pitchYBot: number;
  attackRight: boolean;
  teamIndex: number;
  onPlayerClick: (id: number) => void;
}) {
  const joueurs = equipe.titulaires;
  const pitchW = xEnd - xStart;
  const pitchH = pitchYBot - pitchYTop;

  // Groupe par row (row 1 = GK)
  const lignes = new Map<number, Joueur[]>();
  for (const j of joueurs) {
    const { row } = parseGrid(j.grid);
    if (!lignes.has(row)) lignes.set(row, []);
    lignes.get(row)!.push(j);
  }

  const rows = Array.from(lignes.keys()).sort((a, b) => a - b);
  const nbRows = rows.length;

  const tokens: ReactElement[] = [];
  rows.forEach((row, idx) => {
    const ligne = lignes.get(row)!.sort((a, b) => {
      return parseGrid(a.grid).col - parseGrid(b.grid).col;
    });
    const nbCols = ligne.length;

    // Distribution horizontale (GK à gauche pour home, à droite pour away)
    const fraction = (idx + 1) / (nbRows + 1);
    const xPos = attackRight
      ? xStart + pitchW * fraction
      : xEnd - pitchW * fraction;

    ligne.forEach((joueur, ci) => {
      const yPos = pitchYTop + pitchH * ((ci + 1) / (nbCols + 1));
      tokens.push(
        <PlayerToken
          key={`t${teamIndex}-r${row}-c${ci}`}
          joueur={joueur}
          x={xPos}
          y={yPos}
          color={couleur}
          uid={`t${teamIndex}-r${row}-c${ci}`}
          onPlayerClick={onPlayerClick}
        />
      );
    });
  });

  return <>{tokens}</>;
}

export default function PitchView({ compos }: { compos: CompoEquipe[] }) {
  const router = useRouter();
  if (!compos || compos.length === 0) return null;

  const home = compos[0];
  const away = compos[1];
  const handlePlayerClick = (id: number) => router.push(`/player/${id}`);

  // Dimensions SVG — terrain horizontal
  const W = 720;
  const H = 420;
  const MX = 18; // marge horizontale
  const MY = 18; // marge verticale
  const midX = W / 2;
  const midY = H / 2;

  // Zones de jeu intérieures
  const pitchX1 = MX;
  const pitchX2 = W - MX;
  const pitchY1 = MY;
  const pitchY2 = H - MY;

  return (
    <div className="w-full overflow-x-auto">
      <div style={{ maxWidth: 740, margin: "0 auto" }}>
        {/* En-têtes équipes */}
        <div className="flex justify-between items-center mb-sm px-sm">
          <div className="flex items-center gap-sm">
            {home.logo && <img src={home.logo} alt="" className="w-6 h-6 object-contain" />}
            <span className="text-sm font-bold text-on-surface">{home.equipe}</span>
            <span className="text-xs text-on-surface-variant bg-surface-container-high px-sm py-0.5 rounded-full">
              {home.formation}
            </span>
          </div>
          <span className="text-xs text-on-surface-variant opacity-50 font-mono">VS</span>
          <div className="flex items-center gap-sm flex-row-reverse">
            {away.logo && <img src={away.logo} alt="" className="w-6 h-6 object-contain" />}
            <span className="text-sm font-bold text-on-surface">{away.equipe}</span>
            <span className="text-xs text-on-surface-variant bg-surface-container-high px-sm py-0.5 rounded-full">
              {away.formation}
            </span>
          </div>
        </div>

        {/* Terrain SVG horizontal */}
        <svg
          viewBox={`0 0 ${W} ${H}`}
          style={{ width: "100%", borderRadius: 12, display: "block" }}
        >
          {/* Bandes gazon verticales */}
          {Array.from({ length: 12 }, (_, i) => (
            <rect
              key={i}
              x={i * (W / 12)} y={0}
              width={W / 12} height={H}
              fill={i % 2 === 0 ? "#1e7a34" : "#1a6b2e"}
            />
          ))}

          {/* Bordure terrain */}
          <rect
            x={pitchX1} y={pitchY1}
            width={pitchX2 - pitchX1} height={pitchY2 - pitchY1}
            fill="none" stroke="rgba(255,255,255,0.75)" strokeWidth={2} rx={3}
          />

          {/* Ligne médiane verticale */}
          <line x1={midX} y1={pitchY1} x2={midX} y2={pitchY2}
            stroke="rgba(255,255,255,0.75)" strokeWidth={1.5} />

          {/* Cercle central */}
          <circle cx={midX} cy={midY} r={55}
            fill="none" stroke="rgba(255,255,255,0.75)" strokeWidth={1.5} />
          <circle cx={midX} cy={midY} r={3} fill="rgba(255,255,255,0.85)" />

          {/* Surface de réparation gauche (home) */}
          <rect x={pitchX1} y={midY - 110} width={110} height={220}
            fill="none" stroke="rgba(255,255,255,0.6)" strokeWidth={1.5} />
          {/* Petite surface gauche */}
          <rect x={pitchX1} y={midY - 50} width={45} height={100}
            fill="none" stroke="rgba(255,255,255,0.5)" strokeWidth={1.2} />
          {/* Point de penalty gauche */}
          <circle cx={pitchX1 + 80} cy={midY} r={2.5} fill="rgba(255,255,255,0.75)" />
          {/* Arc de penalty gauche */}
          <path
            d={`M ${pitchX1 + 110} ${midY - 38} A 55 55 0 0 1 ${pitchX1 + 110} ${midY + 38}`}
            fill="none" stroke="rgba(255,255,255,0.4)" strokeWidth={1.2} strokeDasharray="4 3"
          />

          {/* Surface de réparation droite (away) */}
          <rect x={pitchX2 - 110} y={midY - 110} width={110} height={220}
            fill="none" stroke="rgba(255,255,255,0.6)" strokeWidth={1.5} />
          {/* Petite surface droite */}
          <rect x={pitchX2 - 45} y={midY - 50} width={45} height={100}
            fill="none" stroke="rgba(255,255,255,0.5)" strokeWidth={1.2} />
          {/* Point de penalty droit */}
          <circle cx={pitchX2 - 80} cy={midY} r={2.5} fill="rgba(255,255,255,0.75)" />
          {/* Arc de penalty droit */}
          <path
            d={`M ${pitchX2 - 110} ${midY - 38} A 55 55 0 0 0 ${pitchX2 - 110} ${midY + 38}`}
            fill="none" stroke="rgba(255,255,255,0.4)" strokeWidth={1.2} strokeDasharray="4 3"
          />

          {/* Buts */}
          <rect x={pitchX1 - 8} y={midY - 26} width={8} height={52}
            fill="none" stroke="rgba(255,255,255,0.7)" strokeWidth={2} />
          <rect x={pitchX2} y={midY - 26} width={8} height={52}
            fill="none" stroke="rgba(255,255,255,0.7)" strokeWidth={2} />

          {/* Arcs de coin */}
          {[
            [pitchX1, pitchY1, 0, 90],
            [pitchX2, pitchY1, 90, 180],
            [pitchX2, pitchY2, 180, 270],
            [pitchX1, pitchY2, 270, 360],
          ].map(([cx, cy, a1, a2], i) => {
            const rad1 = (a1 * Math.PI) / 180;
            const rad2 = (a2 * Math.PI) / 180;
            const r = 10;
            return (
              <path
                key={i}
                d={`M ${cx + r * Math.cos(rad1)} ${cy + r * Math.sin(rad1)} A ${r} ${r} 0 0 1 ${cx + r * Math.cos(rad2)} ${cy + r * Math.sin(rad2)}`}
                fill="none" stroke="rgba(255,255,255,0.5)" strokeWidth={1.2}
              />
            );
          })}

          {/* Indicateurs de camp */}
          <text x={midX / 2} y={pitchY1 + 12}
            textAnchor="middle" fill="rgba(255,255,255,0.35)" fontSize={9} fontFamily="sans-serif">
            ← {home.equipe}
          </text>
          <text x={midX + midX / 2} y={pitchY1 + 12}
            textAnchor="middle" fill="rgba(255,255,255,0.35)" fontSize={9} fontFamily="sans-serif">
            {away.equipe} →
          </text>

          {/* Joueurs home (moitié gauche) */}
          <TeamHalf
            equipe={home}
            couleur="#2196f3"
            xStart={pitchX1 + 20}
            xEnd={midX - 10}
            pitchYTop={pitchY1 + 20}
            pitchYBot={pitchY2 - 20}
            attackRight={true}
            teamIndex={0}
            onPlayerClick={handlePlayerClick}
          />

          {/* Joueurs away (moitié droite) */}
          <TeamHalf
            equipe={away}
            couleur="#e63946"
            xStart={midX + 10}
            xEnd={pitchX2 - 20}
            pitchYTop={pitchY1 + 20}
            pitchYBot={pitchY2 - 20}
            attackRight={false}
            teamIndex={1}
            onPlayerClick={handlePlayerClick}
          />
        </svg>

        {/* Remplaçants */}
        {(home.remplacants?.length > 0 || away.remplacants?.length > 0) && (
          <div className="mt-md grid grid-cols-2 gap-sm">
            {[home, away].map((eq, idx) => (
              <div key={idx}>
                <p className="text-xs text-on-surface-variant mb-xs font-medium">
                  Remplaçants — {eq.equipe}
                </p>
                <div className="flex flex-col gap-0.5">
                  {eq.remplacants.slice(0, 7).map((joueur, i) => (
                    <div key={i} className="flex items-center gap-xs text-xs text-on-surface-variant">
                      {joueur.id ? (
                        <img
                          src={`${PHOTO_BASE}/${joueur.id}.png`}
                          alt=""
                          className="w-5 h-5 rounded-full object-cover bg-surface-container-high flex-shrink-0"
                          onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                        />
                      ) : (
                        <span className="font-mono text-[10px] w-5 text-center opacity-60">#{joueur.numero}</span>
                      )}
                      <span className="truncate">{joueur.nom}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
