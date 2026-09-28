"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Award, FileText, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { EmptyState, ErrorState, Skeleton } from "@/components/shared/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  CERT_STATUS_META,
  certificationApi,
  type CertificationCatalogItem,
  type ProducerCertification,
} from "@/features/producer/api";
import { ApiError } from "@/lib/api";
import { formatDateShort } from "@/lib/format";
import { session } from "@/lib/session";

const EMPTY_DRAFT = {
  certification_id: "",
  certificate_number: "",
  issued_at: "",
  expires_at: "",
};

export default function CertificationsPage() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [catalog, setCatalog] = useState<CertificationCatalogItem[]>([]);
  const [mine, setMine] = useState<ProducerCertification[]>([]);
  const [draft, setDraft] = useState(EMPTY_DRAFT);
  const [file, setFile] = useState<File | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const accessToken = session.getAccessToken();
    if (!accessToken) {
      router.push("/ingresar");
      return;
    }

    setToken(accessToken);
    setError(null);
    try {
      const [available, own] = await Promise.all([
        certificationApi.catalog(accessToken),
        certificationApi.mine(accessToken),
      ]);
      setCatalog(available);
      setMine(own);
    } catch (requestError) {
      setError(
        requestError instanceof ApiError && requestError.status === 403
          ? "Esta sección es para vendedores aprobados."
          : "No pudimos cargar tus certificaciones.",
      );
    } finally {
      setIsLoading(false);
    }
  }, [router]);

  useEffect(() => {
    void load();
  }, [load]);

  async function add() {
    if (!token || !draft.certification_id) {
      toast.error("Elige la certificación que quieres registrar.");
      return;
    }

    setIsSaving(true);
    try {
      const created = await certificationApi.add(token, {
        certification_id: Number(draft.certification_id),
        certificate_number: draft.certificate_number || undefined,
        issued_at: draft.issued_at || undefined,
        expires_at: draft.expires_at || undefined,
        file,
      });
      setMine((current) => [...current, created]);
      setDraft(EMPTY_DRAFT);
      setFile(null);
      toast.success("Certificación registrada.");
    } catch (requestError) {
      toast.error(
        requestError instanceof ApiError
          ? requestError.message
          : "No pudimos registrar la certificación.",
      );
    } finally {
      setIsSaving(false);
    }
  }

  async function remove(certificationId: string) {
    if (!token) return;
    try {
      await certificationApi.remove(token, certificationId);
      setMine((current) => current.filter((item) => item.id !== certificationId));
      toast.success("Certificación eliminada.");
    } catch {
      toast.error("No pudimos eliminarla.");
    }
  }

  async function openDocument(certificationId: string) {
    if (!token) return;
    try {
      const link = await certificationApi.documentLink(token, certificationId);
      // El enlace caduca en minutos; se abre en el momento en que se pide.
      window.open(link.url, "_blank", "noopener,noreferrer");
    } catch {
      toast.error("No pudimos abrir el documento.");
    }
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      <Link
        href="/productor"
        className="mb-6 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
        Volver a mi panel
      </Link>

      <h1 className="font-display text-3xl font-bold">Certificaciones</h1>
      <p className="mb-8 mt-1 text-muted-foreground">
        Respaldan lo que tus cafés afirman ser. Solo puedes declarar en un café una
        certificación registrada aquí y vigente.
      </p>

      {isLoading && <Skeleton className="h-40 w-full" />}
      {!isLoading && error && <ErrorState title={error} onRetry={() => void load()} />}

      {!isLoading && !error && (
        <div className="space-y-10">
          <section aria-labelledby="mis-certificaciones">
            <h2
              id="mis-certificaciones"
              className="mb-4 font-display text-lg font-semibold"
            >
              Mis certificaciones
            </h2>

            {mine.length === 0 ? (
              <EmptyState
                icon={<Award className="size-10" aria-hidden="true" />}
                title="Todavía no registras certificaciones"
                description="Agrega la primera con su documento y su vigencia."
              />
            ) : (
              <ul className="space-y-3">
                {mine.map((item) => {
                  const meta = CERT_STATUS_META[item.status];
                  return (
                    <li
                      key={item.id}
                      className="flex flex-wrap items-center gap-4 rounded-lg border border-border bg-card p-4"
                    >
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <h3 className="font-medium">{item.certification_name}</h3>
                          <Badge variant={meta.tone}>{meta.label}</Badge>
                        </div>

                        <p className="mt-1 text-sm text-muted-foreground">
                          {item.certificate_number && (
                            <>Nº {item.certificate_number} · </>
                          )}
                          {item.expires_at
                            ? `Vence el ${formatDateShort(item.expires_at)}`
                            : "Sin fecha de vencimiento"}
                          {item.days_to_expiry !== null &&
                            item.days_to_expiry >= 0 &&
                            item.days_to_expiry <= 60 && (
                              <> · quedan {item.days_to_expiry} días</>
                            )}
                        </p>
                      </div>

                      <div className="flex items-center gap-2">
                        {item.has_document && (
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={() => void openDocument(item.id)}
                          >
                            <FileText className="mr-1.5 size-4" aria-hidden="true" />
                            Ver documento
                          </Button>
                        )}

                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => void remove(item.id)}
                        >
                          <Trash2 className="size-4" aria-hidden="true" />
                          <span className="sr-only">
                            Eliminar {item.certification_name}
                          </span>
                        </Button>
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>

          <section aria-labelledby="nueva-certificacion">
            <h2
              id="nueva-certificacion"
              className="mb-4 font-display text-lg font-semibold"
            >
              Registrar una certificación
            </h2>

            <div className="grid gap-4 rounded-lg border border-dashed border-border p-4 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <label
                  htmlFor="certificacion"
                  className="mb-1.5 block text-sm font-medium"
                >
                  Certificación <span aria-hidden="true">*</span>
                </label>
                <select
                  id="certificacion"
                  className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm"
                  value={draft.certification_id}
                  onChange={(event) =>
                    setDraft({ ...draft, certification_id: event.target.value })
                  }
                >
                  <option value="">Elige una…</option>
                  {catalog.map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.name}
                      {option.issuing_body ? ` — ${option.issuing_body}` : ""}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="numero" className="mb-1.5 block text-sm font-medium">
                  Número de certificado
                </label>
                <Input
                  id="numero"
                  value={draft.certificate_number}
                  onChange={(event) =>
                    setDraft({ ...draft, certificate_number: event.target.value })
                  }
                  maxLength={100}
                />
              </div>

              <div>
                <label htmlFor="documento" className="mb-1.5 block text-sm font-medium">
                  Documento (PDF o imagen)
                </label>
                <input
                  id="documento"
                  type="file"
                  accept="application/pdf,image/jpeg,image/png,image/webp"
                  className="w-full text-sm file:mr-3 file:rounded-md file:border-0 file:bg-muted file:px-3 file:py-2 file:text-sm"
                  onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                />
              </div>

              <div>
                <label htmlFor="emision" className="mb-1.5 block text-sm font-medium">
                  Fecha de emisión
                </label>
                <Input
                  id="emision"
                  type="date"
                  value={draft.issued_at}
                  onChange={(event) =>
                    setDraft({ ...draft, issued_at: event.target.value })
                  }
                />
              </div>

              <div>
                <label htmlFor="vencimiento" className="mb-1.5 block text-sm font-medium">
                  Fecha de vencimiento
                </label>
                <Input
                  id="vencimiento"
                  type="date"
                  value={draft.expires_at}
                  onChange={(event) =>
                    setDraft({ ...draft, expires_at: event.target.value })
                  }
                />
              </div>

              <div className="sm:col-span-2">
                <Button
                  type="button"
                  onClick={() => void add()}
                  disabled={isSaving}
                  aria-busy={isSaving}
                >
                  <Plus className="mr-1.5 size-4" aria-hidden="true" />
                  {isSaving ? "Guardando…" : "Registrar certificación"}
                </Button>
                <p className="mt-2 text-xs text-muted-foreground">
                  El documento es privado: solo tú y el equipo de MONK GRAIN pueden
                  abrirlo.
                </p>
              </div>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
