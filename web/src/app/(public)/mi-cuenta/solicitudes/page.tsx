"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Megaphone, Plus } from "lucide-react";

import { EmptyState, ErrorState, Skeleton } from "@/components/shared/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { geoApi, type GeoItem } from "@/features/account/api";
import {
  DEMAND_STATUS_META,
  demandsApi,
  type DemandInput,
  type DemandSummary,
} from "@/features/trading/api";
import { ApiError } from "@/lib/api";
import { formatDateShort, formatKilosWithCargas, formatPricePerKilo } from "@/lib/format";
import { session } from "@/lib/session";
import { PROCESS_LABELS } from "@/types/catalog";

/**
 * Solicitudes de compra del comprador.
 *
 * Es la mitad del mercado que el catálogo no cubre: en vez de recorrer los lotes
 * publicados cada semana, el comprador dice qué busca y a qué precio, y los
 * caficultores le responden con posturas respaldadas por un lote real.
 */

/** Vigencia por defecto, en días. Un mes es lo que suele tardar en armarse una
 *  carga con varios vendedores; el servidor admite hasta 90. */
const DEFAULT_VALIDITY_DAYS = 30;

function defaultExpiry(): string {
  const date = new Date();
  date.setDate(date.getDate() + DEFAULT_VALIDITY_DAYS);
  return date.toISOString().slice(0, 10);
}

export default function BuyerDemandsPage() {
  const router = useRouter();
  const [demands, setDemands] = useState<DemandSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(false);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    const token = session.getAccessToken();
    if (!token) {
      router.push("/ingresar");
      return;
    }

    setError(false);
    try {
      const page = await demandsApi.mine(token);
      setDemands(page.items);
      setIsFormOpen(page.items.length === 0);
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.isUnauthorized) {
        router.push("/ingresar");
        return;
      }
      setError(true);
    } finally {
      setIsLoading(false);
    }
  }, [router]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <Link
        href="/mi-cuenta"
        className="mb-6 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
        Volver a mi cuenta
      </Link>

      <h1 className="font-display text-3xl font-bold">Lo que estoy buscando</h1>
      <p className="mb-8 mt-1 text-muted-foreground">
        Publica los kilos que necesitas y las condiciones que aceptas. Los caficultores
        con lotes que encajen te responderán con su precio, y tú decides.
      </p>

      <div aria-live="polite" className="sr-only">
        {notice}
      </div>

      {isLoading && <Skeleton className="h-48 w-full" />}
      {!isLoading && error && <ErrorState onRetry={() => void load()} />}

      {!isLoading && !error && (
        <div className="space-y-6">
          {demands.length > 0 && (
            <ul className="space-y-4">
              {demands.map((demand) => {
                const meta = DEMAND_STATUS_META[demand.status];
                return (
                  <li key={demand.id}>
                    <Card>
                      <CardContent className="pt-6">
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div className="min-w-0">
                            <Link
                              href={`/mi-cuenta/solicitudes/${demand.id}`}
                              className="font-display font-semibold hover:text-primary"
                            >
                              {demand.title}
                            </Link>
                            <p className="mt-1 text-sm text-muted-foreground">
                              {formatKilosWithCargas(demand.wanted_kg)}
                              {demand.covered_kg > 0 &&
                                ` · cubiertos ${formatKilosWithCargas(demand.covered_kg)}`}
                            </p>
                            <p className="text-sm text-muted-foreground">
                              {demand.max_yield_factor &&
                                `Factor ≤ ${demand.max_yield_factor} · `}
                              {demand.max_moisture_pct &&
                                `Humedad ≤ ${demand.max_moisture_pct} % · `}
                              {demand.process && `${PROCESS_LABELS[demand.process]} · `}
                              {demand.offered_price_per_kg
                                ? `ofreces ${formatPricePerKilo(demand.offered_price_per_kg)}`
                                : "sin precio declarado"}
                            </p>
                            <p className="mt-1 text-xs text-muted-foreground">
                              {demand.is_receiving
                                ? `Vigente hasta el ${formatDateShort(demand.expires_on)}`
                                : "Ya no recibe posturas"}
                            </p>
                          </div>

                          <div className="flex shrink-0 flex-col items-end gap-2">
                            <Badge variant={meta.variant}>{meta.label}</Badge>
                            <Link
                              href={`/mi-cuenta/solicitudes/${demand.id}`}
                              className="text-sm text-primary hover:underline"
                            >
                              {demand.offer_count === 0
                                ? "Sin posturas aún"
                                : demand.offer_count === 1
                                  ? "1 postura"
                                  : `${demand.offer_count} posturas`}
                            </Link>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </li>
                );
              })}
            </ul>
          )}

          {isFormOpen ? (
            <Card>
              <CardContent className="pt-6">
                <DemandForm
                  onCreated={async (message) => {
                    setNotice(message);
                    setIsFormOpen(false);
                    await load();
                  }}
                  onCancel={demands.length > 0 ? () => setIsFormOpen(false) : undefined}
                />
              </CardContent>
            </Card>
          ) : (
            <Button variant="outline" onClick={() => setIsFormOpen(true)}>
              <Plus className="size-4" aria-hidden="true" />
              Publicar otra solicitud
            </Button>
          )}

          {demands.length === 0 && !isFormOpen && (
            <EmptyState
              icon={<Megaphone className="size-10" aria-hidden="true" />}
              title="No has publicado ninguna solicitud"
              description="Dile al mercado qué pergamino necesitas y deja que te busquen."
              action={
                <Button onClick={() => setIsFormOpen(true)}>
                  <Plus className="size-4" aria-hidden="true" />
                  Publicar solicitud
                </Button>
              }
            />
          )}
        </div>
      )}
    </div>
  );
}

function DemandForm({
  onCreated,
  onCancel,
}: {
  onCreated: (message: string) => Promise<void>;
  onCancel?: () => void;
}) {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [wantedKg, setWantedKg] = useState("625");
  const [maxYieldFactor, setMaxYieldFactor] = useState("94");
  const [maxMoisture, setMaxMoisture] = useState("12");
  const [variety, setVariety] = useState("");
  const [process, setProcess] = useState("");
  const [offeredPrice, setOfferedPrice] = useState("");
  const [expiresOn, setExpiresOn] = useState(defaultExpiry());

  const [departments, setDepartments] = useState<GeoItem[]>([]);
  const [departmentId, setDepartmentId] = useState<number | "">("");
  const [municipalities, setMunicipalities] = useState<GeoItem[]>([]);
  const [municipalityId, setMunicipalityId] = useState<number | "">("");

  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    void geoApi
      .departments()
      .then(setDepartments)
      .catch(() => setDepartments([]));
  }, []);

  useEffect(() => {
    if (departmentId === "") {
      setMunicipalities([]);
      return;
    }
    void geoApi
      .municipalities(departmentId)
      .then(setMunicipalities)
      .catch(() => setMunicipalities([]));
  }, [departmentId]);

  async function handleSubmit(event: React.FormEvent): Promise<void> {
    event.preventDefault();
    const token = session.getAccessToken();
    if (!token) {
      router.push("/ingresar");
      return;
    }

    setFormError(null);
    setFieldErrors({});
    const errors: Record<string, string> = {};
    if (title.trim().length < 5)
      errors.title = "Escribe un título de al menos 5 caracteres.";
    if (!wantedKg || Number(wantedKg) < 1)
      errors.wanted_kg = "Indica cuántos kilos buscas.";
    if (!expiresOn) errors.expires_on = "Indica hasta cuándo tiene sentido responderte.";
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      return;
    }

    const payload: DemandInput = {
      title: title.trim(),
      description: description.trim() || null,
      wanted_kg: Number(wantedKg),
      // Vacío es «no pongo ese límite», no cero.
      max_yield_factor: maxYieldFactor.trim() || null,
      max_moisture_pct: maxMoisture.trim() || null,
      variety: variety.trim() || null,
      process: (process || null) as DemandInput["process"],
      municipality_id: municipalityId === "" ? null : municipalityId,
      offered_price_per_kg: offeredPrice.trim() || null,
      expires_on: expiresOn,
    };

    setIsSaving(true);
    try {
      await demandsApi.create(token, payload);
      await onCreated("Solicitud publicada. Los vendedores ya pueden verla.");
    } catch (requestError) {
      if (requestError instanceof ApiError) {
        setFieldErrors(requestError.fieldErrors);
        setFormError(requestError.message);
      } else {
        setFormError("No pudimos publicar la solicitud. Inténtalo de nuevo.");
      }
    } finally {
      setIsSaving(false);
    }
  }

  const selectClass =
    "h-11 w-full rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-50";

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-4">
      <h2 className="flex items-center gap-2 font-display text-lg font-semibold">
        <Megaphone className="size-5 text-primary" aria-hidden="true" />
        Publicar una solicitud
      </h2>

      {formError && (
        <p
          className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive"
          role="alert"
        >
          {formError}
        </p>
      )}

      <div>
        <Label htmlFor="title" required>
          Qué buscas
        </Label>
        <Input
          id="title"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          maxLength={180}
          placeholder="Busco 5 cargas de pergamino, factor 94 o mejor"
          error={fieldErrors.title}
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <Label htmlFor="wanted_kg" required>
            Kilos que necesitas
          </Label>
          <Input
            id="wanted_kg"
            type="number"
            min={1}
            step={125}
            value={wantedKg}
            onChange={(event) => setWantedKg(event.target.value)}
            error={fieldErrors.wanted_kg}
          />
          <p className="mt-1.5 text-xs text-muted-foreground">125 kg = 1 carga</p>
        </div>

        <div>
          <Label htmlFor="offered_price">Precio que ofreces por kilo</Label>
          <Input
            id="offered_price"
            type="number"
            min={1}
            step={100}
            value={offeredPrice}
            onChange={(event) => setOfferedPrice(event.target.value)}
            error={fieldErrors.offered_price_per_kg}
          />
          <p className="mt-1.5 text-xs text-muted-foreground">
            Es una referencia: cada postura trae su propio precio.
          </p>
        </div>

        <div>
          <Label htmlFor="max_yield_factor">Factor máximo que aceptas</Label>
          <Input
            id="max_yield_factor"
            type="number"
            min={80}
            max={130}
            step={0.5}
            value={maxYieldFactor}
            onChange={(event) => setMaxYieldFactor(event.target.value)}
            error={fieldErrors.max_yield_factor}
          />
          <p className="mt-1.5 text-xs text-muted-foreground">
            Menos es mejor café. Déjalo vacío si no pones ese límite.
          </p>
        </div>

        <div>
          <Label htmlFor="max_moisture">Humedad máxima (%)</Label>
          <Input
            id="max_moisture"
            type="number"
            min={0}
            max={100}
            step={0.1}
            value={maxMoisture}
            onChange={(event) => setMaxMoisture(event.target.value)}
            error={fieldErrors.max_moisture_pct}
          />
        </div>

        <div>
          <Label htmlFor="variety">Variedad</Label>
          <Input
            id="variety"
            value={variety}
            onChange={(event) => setVariety(event.target.value)}
            maxLength={100}
            placeholder="Cualquiera"
          />
        </div>

        <div>
          <Label htmlFor="process">Proceso</Label>
          <select
            id="process"
            value={process}
            onChange={(event) => setProcess(event.target.value)}
            className={selectClass}
          >
            <option value="">Cualquiera</option>
            {Object.entries(PROCESS_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <Label htmlFor="demand_department">Departamento de origen</Label>
          <select
            id="demand_department"
            value={departmentId}
            onChange={(event) => {
              setDepartmentId(event.target.value ? Number(event.target.value) : "");
              setMunicipalityId("");
            }}
            className={selectClass}
          >
            <option value="">Cualquiera</option>
            {departments.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <Label htmlFor="demand_municipality">Municipio</Label>
          <select
            id="demand_municipality"
            value={municipalityId}
            disabled={departmentId === ""}
            onChange={(event) =>
              setMunicipalityId(event.target.value ? Number(event.target.value) : "")
            }
            className={selectClass}
          >
            <option value="">
              {departmentId === "" ? "Elige el departamento primero" : "Cualquiera"}
            </option>
            {municipalities.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </div>

        <div className="sm:col-span-2">
          <Label htmlFor="expires_on" required>
            Hasta cuándo tiene sentido responderte
          </Label>
          <Input
            id="expires_on"
            type="date"
            value={expiresOn}
            onChange={(event) => setExpiresOn(event.target.value)}
            error={fieldErrors.expires_on}
          />
          <p className="mt-1.5 text-xs text-muted-foreground">
            Máximo 90 días: más allá, el precio que ofreces ya no corresponde a la
            cosecha.
          </p>
        </div>

        <div className="sm:col-span-2">
          <Label htmlFor="description">Detalles</Label>
          <textarea
            id="description"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            rows={3}
            maxLength={2000}
            placeholder="Dónde recibes, cómo pagas, si exiges análisis en bodega."
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          />
        </div>
      </div>

      <div className="flex flex-wrap gap-3">
        <Button type="submit" isLoading={isSaving}>
          Publicar solicitud
        </Button>
        {onCancel && (
          <Button type="button" variant="outline" onClick={onCancel} disabled={isSaving}>
            Cancelar
          </Button>
        )}
      </div>
    </form>
  );
}
