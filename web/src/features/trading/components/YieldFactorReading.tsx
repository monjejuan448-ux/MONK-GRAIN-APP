"use client";

import { Badge } from "@/components/ui/badge";
import { yieldFactorQuality } from "@/types/catalog";

/**
 * El factor de rendimiento con su lectura comercial al lado.
 *
 * Un «91,50» no le dice nada a quien no sabe que el estándar de la Federación
 * es 94 y que **menos es mejor**. Este componente nunca muestra el número
 * solo: o va con su etiqueta, o dice que no se declaró.
 *
 * La traducción vive en `yieldFactorQuality`, compartida con el catálogo: dos
 * lecturas del mismo número en pantallas distintas sería peor que ninguna.
 */
export function YieldFactorReading({
  factor,
  /** Cuando es un techo y no una medida: «92 o mejor» en vez de «92». */
  asCeiling = false,
}: {
  factor: string | null;
  asCeiling?: boolean;
}) {
  if (factor === null) {
    return <span className="text-muted-foreground">Cualquier factor</span>;
  }

  const quality = yieldFactorQuality(factor);

  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="font-medium tabular-nums">
        {factor}
        {asCeiling && <span className="text-muted-foreground"> o mejor</span>}
      </span>
      {quality && <Badge variant={quality.variant}>{quality.label}</Badge>}
    </span>
  );
}
