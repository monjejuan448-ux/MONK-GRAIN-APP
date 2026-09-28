import { cn } from "@/lib/utils";

/**
 * Identidad de MONK GRAIN.
 *
 * El símbolo combina un grano de café con la silueta de una montaña: el grano
 * es el producto, la montaña es el origen de altura que define su calidad. La
 * hendidura central del grano hace de valle entre las dos cumbres, de modo que
 * ambas lecturas comparten el mismo trazo.
 */

interface LogoProps {
  className?: string;
  showWordmark?: boolean;
  /** Un solo color, para fondos oscuros o impresión a una tinta. */
  monochrome?: boolean;
}

export function Logo({ className, showWordmark = true, monochrome = false }: LogoProps) {
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <LogoMark className="h-9 w-9 shrink-0" monochrome={monochrome} />
      {showWordmark && (
        <span className="flex flex-col leading-none">
          <span className="font-display text-lg font-semibold tracking-tight">
            MONK GRAIN
          </span>
          <span className="text-[0.625rem] uppercase tracking-[0.18em] text-muted-foreground">
            Café de origen
          </span>
        </span>
      )}
    </span>
  );
}

export function LogoMark({
  className,
  monochrome = false,
}: {
  className?: string;
  monochrome?: boolean;
}) {
  const mountain = monochrome ? "currentColor" : "#1F4D3A";
  const bean = monochrome ? "currentColor" : "#6F4E37";
  const seam = monochrome ? "currentColor" : "#C79A55";

  return (
    <svg
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      role="img"
      aria-label="MONK GRAIN"
    >
      {/* Montañas: el origen de altura */}
      <path
        d="M4 38 L15 20 L21 29 L30 14 L44 38 Z"
        fill={mountain}
        opacity={monochrome ? 0.35 : 0.9}
      />
      {/* Grano de café, apoyado sobre el paisaje */}
      <ellipse
        cx="24"
        cy="29"
        rx="11"
        ry="8.5"
        transform="rotate(-24 24 29)"
        fill={bean}
      />
      {/* Hendidura del grano, que continúa la línea del valle */}
      <path
        d="M16 32.5 C19 28.5, 23 26, 31.5 25"
        stroke={seam}
        strokeWidth="2"
        strokeLinecap="round"
        fill="none"
      />
    </svg>
  );
}
