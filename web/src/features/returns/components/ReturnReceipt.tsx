"use client";

import Link from "next/link";
import { CalendarClock, FileText, Truck } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { RETURN_STATUS_META, type ReturnDetail } from "@/features/returns/api";
import { formatCurrency, formatDate } from "@/lib/format";

/**
 * Constancia de la reclamación.
 *
 * Es la misma para el comprador y para quien vende: ambos deben ver
 * exactamente lo que se radicó, con su número, su fecha y los plazos que
 * corren. Lo que cambia entre uno y otro son las acciones disponibles, que
 * cada página añade aparte.
 */
export function ReturnReceipt({ request }: { request: ReturnDetail }) {
  const meta = RETURN_STATUS_META[request.status];

  return (
    <div className="space-y-6">
      <Card>
        <CardContent className="pt-6">
          <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="font-display text-xl font-bold">{request.return_number}</h2>
              <p className="text-sm text-muted-foreground">
                Radicada el {formatDate(request.filed_at)} · pedido {request.order_number}{" "}
                · {request.producer_name}
              </p>
            </div>
            <Badge variant={meta.variant} size="md">
              {meta.label}
            </Badge>
          </div>

          <dl className="grid gap-4 sm:grid-cols-2">
            <div>
              <dt className="text-sm text-muted-foreground">Motivo</dt>
              <dd className="font-medium capitalize">{request.reason_label}</dd>
            </div>
            <div>
              <dt className="text-sm text-muted-foreground">Importe a reembolsar</dt>
              <dd className="font-display font-semibold">
                {request.refund_amount ? formatCurrency(request.refund_amount) : "—"}
              </dd>
            </div>
          </dl>

          {request.description && (
            <div className="mt-5">
              <h3 className="text-sm text-muted-foreground">Lo que nos contaron</h3>
              <p className="mt-1 whitespace-pre-line text-sm">{request.description}</p>
            </div>
          )}

          <ul className="mt-5 divide-y divide-border border-t border-border">
            {request.items.map((item) => (
              <li
                key={item.id}
                className="flex items-baseline justify-between gap-4 py-2"
              >
                <span className="min-w-0">
                  <span className="block truncate">{item.product_name}</span>
                  <span className="text-sm text-muted-foreground">
                    {item.variant_label} · {item.quantity}{" "}
                    {item.quantity === 1 ? "unidad" : "unidades"}
                  </span>
                </span>
                <span className="whitespace-nowrap font-medium">
                  {formatCurrency(item.line_refund)}
                </span>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="space-y-3 pt-6 text-sm">
          <h3 className="font-display font-semibold">Plazos y condiciones</h3>

          <p className="flex gap-2">
            <CalendarClock
              className="mt-0.5 size-4 shrink-0 text-muted-foreground"
              aria-hidden="true"
            />
            <span>
              Respuesta escrita a más tardar el{" "}
              <strong>{formatDate(request.response_due_at)}</strong> (quince días hábiles,
              Decreto 735 de 2013).
            </span>
          </p>

          <p className="flex gap-2">
            <CalendarClock
              className="mt-0.5 size-4 shrink-0 text-muted-foreground"
              aria-hidden="true"
            />
            <span>
              Devolución del dinero a más tardar el{" "}
              <strong>{formatDate(request.refund_due_at)}</strong>
              {request.reason === "withdrawal"
                ? ", contados desde que se ejerció el retracto."
                : "."}
            </span>
          </p>

          <p className="flex gap-2">
            <Truck
              className="mt-0.5 size-4 shrink-0 text-muted-foreground"
              aria-hidden="true"
            />
            <span>
              El transporte de la devolución corre por cuenta de{" "}
              <strong>
                {request.return_shipping_paid_by_seller ? "quien vende" : "quien compra"}
              </strong>
              {request.return_shipping_paid_by_seller
                ? " (numeral 1 del artículo 11 de la Ley 1480 de 2011)."
                : ", como dispone el artículo 47 para el retracto."}
            </span>
          </p>

          {request.declared_unopened && (
            <p className="text-muted-foreground">
              El comprador declaró que el empaque sigue sellado y sin abrir.
            </p>
          )}
        </CardContent>
      </Card>

      {request.resolution_notes && (
        <Card>
          <CardContent className="pt-6">
            <h3 className="font-display font-semibold">
              Respuesta
              {request.reviewed_at && <> del {formatDate(request.reviewed_at)}</>}
            </h3>
            <p className="mt-2 whitespace-pre-line text-sm">{request.resolution_notes}</p>

            {request.status === "rejected" && (
              <p className="mt-4 rounded-md border border-border bg-muted/40 p-3 text-sm">
                Si no estás de acuerdo, conserva el número{" "}
                <strong>{request.return_number}</strong> y acude a la{" "}
                <a
                  href="https://www.sic.gov.co"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline"
                >
                  Superintendencia de Industria y Comercio
                </a>
                . No necesitas abogado. Consulta el detalle en{" "}
                <Link href="/legal/devoluciones" className="underline">
                  devoluciones y reembolsos
                </Link>
                .
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {request.evidences.length > 0 && (
        <Card>
          <CardContent className="pt-6">
            <h3 className="mb-3 font-display font-semibold">Fotografías adjuntas</h3>
            <ul className="flex flex-wrap gap-2">
              {request.evidences.map((evidence) => (
                <li key={evidence.id}>
                  {/*
                    Los enlaces son firmados y caducan en minutos, así que se
                    abren en el momento en que se piden y no se guardan.
                  */}
                  <a
                    href={evidence.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-2 text-sm hover:bg-muted"
                  >
                    <FileText className="size-4" aria-hidden="true" />
                    Ver fotografía del {formatDate(evidence.created_at)}
                  </a>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
