"use client";

import { Badge } from "@/components/ui/badge";
import { OFFER_STATUS_META, type OfferStatus } from "@/features/trading/api";

/**
 * Qué respondió el comprador a una postura.
 *
 * Lo que hace este componente y no haría un `Badge` suelto: **el motivo del
 * rechazo se muestra completo**. Es lo que le dice al caficultor qué ajustar
 * en la siguiente postura —si fue el precio, el factor o la cantidad—, y
 * esconderlo tras un «ver más» convierte el rechazo en un «no» sin salida.
 *
 * Un rechazo sin motivo se dice con esas palabras, en lugar de dejar el hueco
 * vacío: un recuadro en blanco parece un fallo de la página.
 */
export function OfferResponse({
  status,
  responseNote,
}: {
  status: OfferStatus;
  responseNote: string | null;
}) {
  const meta = OFFER_STATUS_META[status];

  return (
    <div className="space-y-1">
      <Badge variant={meta.variant}>{meta.label}</Badge>

      {status === "rejected" && (
        <p className="max-w-prose text-sm text-muted-foreground">
          {responseNote ?? (
            <span className="italic">El comprador no explicó el motivo.</span>
          )}
        </p>
      )}
    </div>
  );
}
