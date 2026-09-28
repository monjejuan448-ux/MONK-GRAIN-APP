"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useCallback } from "react";
import { X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PROCESS_LABELS } from "@/types/catalog";

const REGIONS = [
  { value: "huila", label: "Huila" },
  { value: "narino", label: "Nariño" },
  { value: "cauca", label: "Cauca" },
  { value: "tolima", label: "Tolima" },
  { value: "eje_cafetero", label: "Eje Cafetero" },
  { value: "antioquia", label: "Antioquia" },
  { value: "santander", label: "Santander" },
  { value: "sierra_nevada", label: "Sierra Nevada" },
];

const CERTIFICATIONS = [
  { value: "organic", label: "Orgánico" },
  { value: "fairtrade", label: "Comercio Justo" },
  { value: "rainforest", label: "Rainforest Alliance" },
  { value: "denominacion_origen", label: "Denominación de Origen" },
  { value: "bird_friendly", label: "Bird Friendly" },
];

const SORT_OPTIONS = [
  { value: "newest", label: "Más recientes" },
  { value: "price_asc", label: "Precio por kilo: menor a mayor" },
  { value: "price_desc", label: "Precio por kilo: mayor a menor" },
  // Ascendente: en el factor de rendimiento, menos es mejor.
  { value: "yield_factor", label: "Mejor factor de rendimiento" },
  { value: "rating", label: "Mejor calificados" },
  { value: "popular", label: "Más vendidos" },
];

/** Techos de factor que se ofrecen como atajo, siguiendo la práctica comercial:
 *  94 es el estándar de la Federación y por debajo de 90 se paga sobreprecio. */
const YIELD_FACTOR_LIMITS = [
  { value: "89", label: "≤ 89", hint: "Excepcional" },
  { value: "92", label: "≤ 92", hint: "De exportación" },
  { value: "94", label: "≤ 94", hint: "Estándar" },
];

/** Volúmenes frecuentes, en cargas de 125 kg. */
const VOLUME_OPTIONS = [
  { value: "125", label: "1 carga" },
  { value: "625", label: "5 cargas" },
  { value: "1250", label: "10 cargas" },
  { value: "6250", label: "50 cargas" },
];

/** Etiquetas legibles de los filtros activos, para poder retirarlos uno a uno. */
const FILTER_LABELS: Record<string, (value: string) => string> = {
  q: (v) => `"${v}"`,
  region: (v) => REGIONS.find((r) => r.value === v)?.label ?? v,
  process: (v) => PROCESS_LABELS[v as keyof typeof PROCESS_LABELS] ?? v,
  certification: (v) => CERTIFICATIONS.find((c) => c.value === v)?.label ?? v,
  max_yield_factor: (v) => `Factor ≤ ${v}`,
  max_moisture_pct: (v) => `Humedad ≤ ${v} %`,
  min_available_kg: (v) => `Desde ${Number(v).toLocaleString("es-CO")} kg`,
  max_price: (v) => `Hasta $${Number(v).toLocaleString("es-CO")}/kg`,
};

export function CatalogFilters() {
  const router = useRouter();
  const searchParams = useSearchParams();

  /**
   * Los filtros viven en la URL, no en el estado del componente: así la
   * búsqueda se puede compartir, recargar y navegar con el historial sin
   * perderla (HU-VIS-03, CA3).
   */
  const setFilter = useCallback(
    (key: string, value: string | null) => {
      const params = new URLSearchParams(searchParams.toString());
      if (value) {
        params.set(key, value);
      } else {
        params.delete(key);
      }
      params.delete("page"); // cambiar un filtro vuelve a la primera página
      router.push(`/catalogo?${params.toString()}`);
    },
    [router, searchParams],
  );

  const activeFilters = Array.from(searchParams.entries()).filter(
    ([key]) => key !== "sort" && key !== "page" && key in FILTER_LABELS,
  );

  return (
    <div className="space-y-6">
      {activeFilters.length > 0 && (
        <div>
          <div className="mb-2 flex items-center justify-between">
            <h2 className="text-sm font-semibold">Filtros activos</h2>
            <Button
              variant="link"
              size="sm"
              className="h-auto p-0 text-xs"
              onClick={() => router.push("/catalogo")}
            >
              Limpiar todo
            </Button>
          </div>
          <ul className="flex flex-wrap gap-2">
            {activeFilters.map(([key, value]) => (
              <li key={`${key}-${value}`}>
                <button
                  type="button"
                  onClick={() => setFilter(key, null)}
                  className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-3 py-1.5 text-xs font-medium text-primary hover:bg-primary/20"
                >
                  {FILTER_LABELS[key]?.(value) ?? value}
                  <X className="size-3" aria-hidden="true" />
                  <span className="sr-only">Quitar filtro</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      <FilterGroup
        label="Región"
        options={REGIONS}
        selected={searchParams.get("region")}
        onSelect={(value) => setFilter("region", value)}
      />

      {/* No hay filtro por tipo de café: todo el catálogo es pergamino seco. Lo
          que distingue un lote de otro es su factor y su humedad. */}

      <FilterGroup
        label="Proceso"
        options={Object.entries(PROCESS_LABELS).map(([value, label]) => ({
          value,
          label,
        }))}
        selected={searchParams.get("process")}
        onSelect={(value) => setFilter("process", value)}
      />

      <FilterGroup
        label="Certificación"
        options={CERTIFICATIONS}
        selected={searchParams.get("certification")}
        onSelect={(value) => setFilter("certification", value)}
      />

      <div>
        <h2 className="mb-1 text-sm font-semibold">Factor de rendimiento</h2>
        <p className="mb-2 text-xs text-muted-foreground">
          Kilos de pergamino por saco de 70 kg de excelso. Más bajo es mejor.
        </p>
        <div className="flex flex-wrap gap-2">
          {YIELD_FACTOR_LIMITS.map((limit) => {
            const isSelected = searchParams.get("max_yield_factor") === limit.value;
            return (
              <button
                key={limit.value}
                type="button"
                title={limit.hint}
                aria-pressed={isSelected}
                onClick={() =>
                  setFilter("max_yield_factor", isSelected ? null : limit.value)
                }
                className={`rounded-md border px-3 py-1.5 text-xs transition-colors ${
                  isSelected
                    ? "border-primary bg-primary/10 text-primary"
                    : "border-border hover:bg-muted"
                }`}
              >
                {limit.label}
              </button>
            );
          })}
        </div>
      </div>

      <div>
        <h2 className="mb-1 text-sm font-semibold">Humedad máxima</h2>
        <p className="mb-2 text-xs text-muted-foreground">
          Por encima del 12 % hay riesgo de hongos.
        </p>
        <div className="flex flex-wrap gap-2">
          {["11", "11.5", "12"].map((limit) => {
            const isSelected = searchParams.get("max_moisture_pct") === limit;
            return (
              <button
                key={limit}
                type="button"
                aria-pressed={isSelected}
                onClick={() => setFilter("max_moisture_pct", isSelected ? null : limit)}
                className={`rounded-md border px-3 py-1.5 text-xs transition-colors ${
                  isSelected
                    ? "border-primary bg-primary/10 text-primary"
                    : "border-border hover:bg-muted"
                }`}
              >
                ≤ {limit.replace(".", ",")} %
              </button>
            );
          })}
        </div>
      </div>

      <div>
        <h2 className="mb-1 text-sm font-semibold">Volumen disponible</h2>
        <p className="mb-2 text-xs text-muted-foreground">
          Oculta los lotes que no alcanzan para lo que necesitas.
        </p>
        <div className="flex flex-wrap gap-2">
          {VOLUME_OPTIONS.map((option) => {
            const isSelected = searchParams.get("min_available_kg") === option.value;
            return (
              <button
                key={option.value}
                type="button"
                aria-pressed={isSelected}
                onClick={() =>
                  setFilter("min_available_kg", isSelected ? null : option.value)
                }
                className={`rounded-md border px-3 py-1.5 text-xs transition-colors ${
                  isSelected
                    ? "border-primary bg-primary/10 text-primary"
                    : "border-border hover:bg-muted"
                }`}
              >
                {option.label}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function FilterGroup({
  label,
  options,
  selected,
  onSelect,
}: {
  label: string;
  options: Array<{ value: string; label: string }>;
  selected: string | null;
  onSelect: (value: string | null) => void;
}) {
  return (
    <fieldset>
      <legend className="mb-2 text-sm font-semibold">{label}</legend>
      <ul className="space-y-1">
        {options.map((option) => {
          const isSelected = selected === option.value;
          return (
            <li key={option.value}>
              <button
                type="button"
                onClick={() => onSelect(isSelected ? null : option.value)}
                aria-pressed={isSelected}
                className={`w-full rounded-md px-2 py-1.5 text-left text-sm transition-colors ${
                  isSelected
                    ? "bg-primary/10 font-medium text-primary"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                }`}
              >
                {option.label}
              </button>
            </li>
          );
        })}
      </ul>
    </fieldset>
  );
}

export function SortSelect() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const current = searchParams.get("sort") ?? "newest";

  return (
    <div className="flex items-center gap-2">
      <label htmlFor="sort" className="whitespace-nowrap text-sm text-muted-foreground">
        Ordenar por
      </label>
      <select
        id="sort"
        value={current}
        onChange={(event) => {
          const params = new URLSearchParams(searchParams.toString());
          params.set("sort", event.target.value);
          params.delete("page");
          router.push(`/catalogo?${params.toString()}`);
        }}
        className="h-9 rounded-md border border-input bg-background px-2 text-sm"
      >
        {SORT_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}

export function ResultCount({ total }: { total: number }) {
  return (
    <Badge variant="outline" aria-live="polite">
      {total === 0
        ? "Sin resultados"
        : `${total} ${total === 1 ? "café encontrado" : "cafés encontrados"}`}
    </Badge>
  );
}
