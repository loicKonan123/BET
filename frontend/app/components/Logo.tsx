/**
 * Logo EDGE — un badge avec une courbe ascendante qui « perce » vers le haut
 * (l'avantage / l'edge). Couleurs émeraude→menthe, thème-aware.
 */
export default function Logo({
  size = 30,
  withWordmark = true,
}: {
  size?: number;
  withWordmark?: boolean;
}) {
  return (
    <span className="flex items-center gap-sm">
      <svg
        width={size}
        height={size}
        viewBox="0 0 32 32"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-label="EDGE"
        role="img"
      >
        <defs>
          <linearGradient id="edgeGrad" x1="4" y1="28" x2="28" y2="4" gradientUnits="userSpaceOnUse">
            <stop stopColor="#10b981" />
            <stop offset="1" stopColor="#6ffbbe" />
          </linearGradient>
        </defs>
        {/* badge */}
        <rect
          x="1.25"
          y="1.25"
          width="29.5"
          height="29.5"
          rx="8.5"
          fill="url(#edgeGrad)"
          fillOpacity="0.12"
          stroke="url(#edgeGrad)"
          strokeWidth="1.5"
        />
        {/* courbe ascendante */}
        <path
          d="M7 21.5 L13 15.5 L17 18.5 L24.5 8.5"
          stroke="url(#edgeGrad)"
          strokeWidth="2.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {/* pointe de flèche (↗) */}
        <path
          d="M24.5 8.5 L19.2 8.5 M24.5 8.5 L24.5 13.8"
          stroke="url(#edgeGrad)"
          strokeWidth="2.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      {withWordmark && (
        <span className="font-display-lg text-headline-lg font-black tracking-tighter text-primary">
          EDGE
        </span>
      )}
    </span>
  );
}
