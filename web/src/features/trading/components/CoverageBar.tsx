"use client";

import { formatKilosWithCargas } from "@/lib/format";

/**
 * Cuánto de una solicitud se ha cubierto ya.
 *
 * Existe porque en pergamino **una solicitud grande no la cubre un solo
 * caficultor**: quien busca diez cargas suele armarlas con tres vendedores. El
 * comprador necesita ver de un vistazo cuánto le falta, y el vendedor, si
 * todavía cabe lo que tiene.
 *
 * Muestra los kilos y el porcentaje juntos a propósito. El porcentaje solo
 * engaña —«80 %» de una solicitud pequeña puede ser menos café que el 20 % de
 * una grande— y los kilos solos obligan a hacer la división mentalmente.
 */
export function CoverageBar({
  wantedKg,
  coveredKg,
  remainingKg,
}: {
  wantedKg: number;
  coveredKg: number;
  remainingKg: number;
}) {
  const percentage = wantedKg > 0 ? Math.round((coveredKg / wantedKg) * 100) : 0;
  const isComplete = remainingKg === 0;

  return (
    <div>
      <div className="flex items-baseline justify-between gap-2 text-sm">
        <span className="tabular-nums">
          {formatKilosWithCargas(coveredKg)} de {formatKilosWithCargas(wantedKg)}
        </span>
        <span
          className={isComplete ? "font-semibold text-forest" : "text-muted-foreground"}
        >
          {percentage} %
        </span>
      </div>

      {/* `role="progressbar"` y sus atributos: un lector de pantalla no ve el
          ancho de un div, así que sin esto la barra no existe para quien
          navega por voz. */}
      <div
        className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-muted"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={wantedKg}
        aria-valuenow={coveredKg}
        aria-label={`Cubierto ${percentage} por ciento`}
      >
        <div
          className={isComplete ? "h-full bg-forest" : "h-full bg-primary"}
          style={{ width: `${percentage}%` }}
        />
      </div>

      {!isComplete && (
        <p className="mt-1 text-xs text-muted-foreground">
          Faltan {formatKilosWithCargas(remainingKg)}
        </p>
      )}
    </div>
  );
}
