"use client";

import Link from "next/link";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CoverageBar } from "@/features/trading/components/CoverageBar";
import { YieldFactorReading } from "@/features/trading/components/YieldFactorReading";
import { DEMAND_STATUS_META, type DemandSummary } from "@/features/trading/api";
import { formatDateShort, formatPricePerKilo } from "@/lib/format";

/**
 * Una solicitud de compra en un listado.
 *
 * La misma tarjeta sirve al comprador —que ve las suyas— y al vendedor —que ve
 * las que puede atender—, con `href` distinto. Dos componentes casi iguales
 * acabarían divergiendo: uno recibiría una mejora y el otro no.
 *
 * El orden de la información sigue la decisión de compra, no el modelo de
 * datos: primero qué busca y cuánto falta, después las condiciones, y el
 * estado al final. Un vendedor decide si postura mirando lo primero.
 */
export function DemandCard({ demand, href }: { demand: DemandSummary; href: string }) {
  const meta = DEMAND_STATUS_META[demand.status];

  return (
    <Card>
      <CardContent className="space-y-3 pt-6">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="min-w-0">
            <Link href={href} className="font-medium hover:text-primary">
              {demand.title}
            </Link>
            <p className="text-sm text-muted-foreground">{demand.buyer_name}</p>
          </div>
          <Badge variant={meta.variant}>{meta.label}</Badge>
        </div>

        <CoverageBar
          wantedKg={demand.wanted_kg}
          coveredKg={demand.covered_kg}
          remainingKg={demand.remaining_kg}
        />

        <dl className="grid gap-x-4 gap-y-1 text-sm sm:grid-cols-2">
          <div className="flex gap-2">
            <dt className="text-muted-foreground">Factor</dt>
            <dd>
              <YieldFactorReading factor={demand.max_yield_factor} asCeiling />
            </dd>
          </div>

          {demand.offered_price_per_kg && (
            <div className="flex gap-2">
              <dt className="text-muted-foreground">Paga hasta</dt>
              <dd className="tabular-nums">
                {formatPricePerKilo(demand.offered_price_per_kg)}
              </dd>
            </div>
          )}

          {demand.municipality && (
            <div className="flex gap-2">
              <dt className="text-muted-foreground">Origen</dt>
              <dd>
                {demand.municipality}
                {demand.department && `, ${demand.department}`}
              </dd>
            </div>
          )}

          <div className="flex gap-2">
            <dt className="text-muted-foreground">Vigente hasta</dt>
            <dd>{formatDateShort(demand.expires_on)}</dd>
          </div>
        </dl>

        <p className="text-sm text-muted-foreground">
          {demand.offer_count === 0
            ? "Sin posturas todavía"
            : `${demand.offer_count} ${demand.offer_count === 1 ? "postura" : "posturas"}`}
          {/* Que ya no reciba posturas se dice aquí y no solo con el estado:
              un vendedor que llega a una solicitud vencida necesita saber por
              qué no puede responder, no deducirlo de una etiqueta. */}
          {!demand.is_receiving && " · ya no recibe posturas"}
        </p>
      </CardContent>
    </Card>
  );
}
