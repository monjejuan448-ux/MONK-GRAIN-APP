"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  DRYING_SUGGESTIONS,
  PROCESS_OPTIONS,
  type ProducerProduct,
  type ProductInput,
} from "@/features/producer/api";

/**
 * Las mismas reglas que aplica el servidor, repetidas aquí para avisar antes de
 * enviar. La validación del cliente es cortesía, no seguridad: el backend
 * vuelve a comprobarlo todo porque nada impide llamar a la API sin pasar por
 * esta pantalla.
 */
/**
 * Un número opcional escrito en un campo de texto: vacío es ausencia de dato.
 */
function optionalNumber(max: number, message: string) {
  return z
    .string()
    .optional()
    .refine((value) => !value || (Number(value) >= 0 && Number(value) <= max), {
      message,
    });
}

const schema = z
  .object({
    name: z
      .string()
      .trim()
      .min(3, "El nombre debe tener al menos 3 caracteres.")
      .max(180),
    description: z
      .string()
      .trim()
      .min(20, "Describe tu lote con al menos 20 caracteres.")
      .max(5000),
    // Los campos numéricos se validan como texto porque eso es lo que entrega
    // un formulario HTML; convertirlos antes de tiempo convierte un campo vacío
    // en cero, que aquí significaría «gratis».
    base_price: z
      .string()
      .min(1, "Indica el precio.")
      .refine((value) => Number(value) > 0, "El precio debe ser mayor que cero."),
    wholesale_price: z.string().optional(),
    lot_code: z.string().max(60).optional(),
    sica_code: z.string().max(40).optional(),
    drying_method: z.string().max(80).optional(),
    notes: z.string().max(2000).optional(),
    dispatch_days: z
      .string()
      .refine((value) => Number(value) >= 1 && Number(value) <= 30, "Entre 1 y 30 días."),
    storage_conditions: z.string().max(1000).optional(),
    allows_samples: z.boolean(),
    variety: z.string().max(100).optional(),
    process: z.string().optional(),
    altitude_masl: optionalNumber(3000, "La altitud debe estar entre 0 y 3000 m."),
    harvest_date: z.string().optional(),

    // El factor solo existe entre 80 y 130: fuera de ahí es un error de
    // digitación, no un café distinto. El mismo rango que la base de datos.
    yield_factor: z
      .string()
      .optional()
      .refine(
        (value) => !value || (Number(value) >= 80 && Number(value) <= 130),
        "El factor de rendimiento va de 80 a 130. El estándar es 94.",
      ),
    moisture_pct: optionalNumber(100, "La humedad va de 0 a 100 %."),
    healthy_bean_pct: optionalNumber(100, "El porcentaje va de 0 a 100."),
    pasilla_pct: optionalNumber(100, "El porcentaje va de 0 a 100."),
    borer_damage_pct: optionalNumber(100, "El porcentaje va de 0 a 100."),
    screen_sizes: z
      .string()
      .optional()
      .refine((value) => {
        if (!value) return true;
        return value
          .split(",")
          .map((part) => part.trim())
          .filter(Boolean)
          .every((part) => {
            const size = Number(part);
            return Number.isInteger(size) && size >= 14 && size <= 20;
          });
      }, "Las mallas válidas van de 14 a 20, separadas por comas."),
  })
  .refine(
    (data) =>
      !data.wholesale_price || Number(data.wholesale_price) < Number(data.base_price),
    {
      message: "El precio por volumen debe ser menor que el precio por kilo corriente.",
      path: ["wholesale_price"],
    },
  );

type FormValues = z.infer<typeof schema>;

interface ProductFormProps {
  product?: ProducerProduct;
  onSubmit: (input: ProductInput) => Promise<void>;
  isSaving: boolean;
}

/** Convierte "" en null: un campo vacío es ausencia de dato, no cadena vacía. */
function orNull(value: string | number | undefined): string | null {
  if (value === undefined || value === "") return null;
  return String(value);
}

export function ProductForm({ product, onSubmit, isSaving }: ProductFormProps) {
  const attributes = product?.attributes;

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: product?.name ?? "",
      description: product?.description ?? "",
      base_price: product?.base_price ?? "",
      wholesale_price: product?.wholesale_price ?? "",
      dispatch_days: String(product?.dispatch_days ?? 3),
      storage_conditions: product?.storage_conditions ?? "",
      allows_samples: product?.allows_samples ?? false,
      variety: attributes?.variety ?? "",
      process: attributes?.process ?? "",
      altitude_masl: attributes?.altitude_masl ? String(attributes.altitude_masl) : "",
      harvest_date: attributes?.harvest_date ?? "",
      yield_factor: attributes?.yield_factor ?? "",
      moisture_pct: attributes?.moisture_pct ?? "",
      healthy_bean_pct: attributes?.healthy_bean_pct ?? "",
      pasilla_pct: attributes?.pasilla_pct ?? "",
      borer_damage_pct: attributes?.borer_damage_pct ?? "",
      screen_sizes: attributes?.screen_sizes?.join(", ") ?? "",
      lot_code: attributes?.lot_code ?? "",
      sica_code: attributes?.sica_code ?? "",
      drying_method: attributes?.drying_method ?? "",
      notes: attributes?.notes ?? "",
    },
  });

  const submit = handleSubmit(async (values) => {
    await onSubmit({
      name: values.name.trim(),
      description: values.description.trim(),
      // Un solo estado posible: no se pregunta, se declara.
      state: "pergamino",
      base_price: values.base_price,
      wholesale_price: orNull(values.wholesale_price),
      dispatch_days: Number(values.dispatch_days),
      storage_conditions: orNull(values.storage_conditions),
      allows_samples: Boolean(values.allows_samples),
      attributes: {
        variety: orNull(values.variety),
        process: orNull(values.process),
        altitude_masl: values.altitude_masl === "" ? null : Number(values.altitude_masl),
        harvest_date: orNull(values.harvest_date),

        yield_factor: orNull(values.yield_factor),
        moisture_pct: orNull(values.moisture_pct),
        healthy_bean_pct: orNull(values.healthy_bean_pct),
        pasilla_pct: orNull(values.pasilla_pct),
        borer_damage_pct: orNull(values.borer_damage_pct),
        screen_sizes: values.screen_sizes
          ? values.screen_sizes
              .split(",")
              .map((part) => Number(part.trim()))
              .filter((size) => Number.isInteger(size))
              .sort((a, b) => a - b)
          : null,

        lot_code: orNull(values.lot_code),
        sica_code: orNull(values.sica_code),
        drying_method: orNull(values.drying_method),
        notes: orNull(values.notes),
      },
    });
  });

  return (
    <form onSubmit={submit} className="space-y-8" noValidate>
      <fieldset className="space-y-4" disabled={isSaving}>
        <legend className="font-display text-lg font-semibold">Tu lote</legend>

        <div>
          <label htmlFor="name" className="mb-1.5 block text-sm font-medium">
            Nombre del lote <span aria-hidden="true">*</span>
          </label>
          <Input
            id="name"
            placeholder="Ej.: Nariño Altura Lavado"
            error={errors.name?.message}
            {...register("name")}
          />
        </div>

        <div>
          <label htmlFor="description" className="mb-1.5 block text-sm font-medium">
            Descripción <span aria-hidden="true">*</span>
          </label>
          <textarea
            id="description"
            rows={4}
            placeholder="Cuenta de qué parcela sale, cómo lo beneficiaste y cómo lo secaste."
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            aria-invalid={errors.description ? true : undefined}
            aria-describedby={errors.description ? "description-error" : undefined}
            {...register("description")}
          />
          {errors.description && (
            <p
              id="description-error"
              role="alert"
              className="mt-1.5 text-sm text-destructive"
            >
              {errors.description.message}
            </p>
          )}
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="dispatch_days" className="mb-1.5 block text-sm font-medium">
              Días para despachar
            </label>
            <Input
              id="dispatch_days"
              type="number"
              min={1}
              max={30}
              error={errors.dispatch_days?.message}
              {...register("dispatch_days")}
            />
          </div>
        </div>
      </fieldset>

      <fieldset className="space-y-4" disabled={isSaving}>
        <legend className="font-display text-lg font-semibold">Precio</legend>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="base_price" className="mb-1.5 block text-sm font-medium">
              Precio por kilo (COP) <span aria-hidden="true">*</span>
            </label>
            <Input
              id="base_price"
              type="number"
              min={1}
              step={100}
              error={errors.base_price?.message}
              {...register("base_price")}
            />
          </div>

          <div>
            <label htmlFor="wholesale_price" className="mb-1.5 block text-sm font-medium">
              Precio por kilo en volumen (opcional)
            </label>
            <Input
              id="wholesale_price"
              type="number"
              min={1}
              step={100}
              error={errors.wholesale_price?.message}
              {...register("wholesale_price")}
            />
          </div>
        </div>
      </fieldset>

      <fieldset className="space-y-4" disabled={isSaving}>
        <legend className="font-display text-lg font-semibold">Origen y beneficio</legend>
        <p className="text-sm text-muted-foreground">
          Todo esto es opcional, pero es lo que un comprador mira para decidir.
        </p>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="variety" className="mb-1.5 block text-sm font-medium">
              Variedad
            </label>
            <Input
              id="variety"
              placeholder="Caturra, Castillo, Geisha…"
              {...register("variety")}
            />
          </div>

          <div>
            <label htmlFor="process" className="mb-1.5 block text-sm font-medium">
              Proceso
            </label>
            <select
              id="process"
              className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm"
              {...register("process")}
            >
              <option value="">Sin especificar</option>
              {PROCESS_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="altitude_masl" className="mb-1.5 block text-sm font-medium">
              Altitud (m s. n. m.)
            </label>
            <Input
              id="altitude_masl"
              type="number"
              min={0}
              max={3000}
              error={errors.altitude_masl?.message}
              {...register("altitude_masl")}
            />
          </div>

          <div>
            <label htmlFor="harvest_date" className="mb-1.5 block text-sm font-medium">
              Fecha de cosecha
            </label>
            <Input id="harvest_date" type="date" {...register("harvest_date")} />
          </div>

          <div>
            <label htmlFor="drying_method" className="mb-1.5 block text-sm font-medium">
              Método de secado
            </label>
            <Input
              id="drying_method"
              list="drying-suggestions"
              placeholder="Marquesina, 18 días"
              error={errors.drying_method?.message}
              {...register("drying_method")}
            />
            {/* Sugerencias, no una lista cerrada: cada finca seca a su manera. */}
            <datalist id="drying-suggestions">
              {DRYING_SUGGESTIONS.map((option) => (
                <option key={option} value={option} />
              ))}
            </datalist>
          </div>
        </div>

        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" className="size-4" {...register("allows_samples")} />
          Envío muestra a quien me la pida antes de una compra por volumen
        </label>
      </fieldset>

      {/* ---------------- Análisis del pergamino ---------------- */}
      <fieldset className="space-y-4" disabled={isSaving}>
        <legend className="font-display text-lg font-semibold">
          Análisis del pergamino
        </legend>
        <p className="text-sm text-muted-foreground">
          Todo es opcional: publica lo que tengas medido. Un lote con su factor y su
          humedad declarados se vende mejor, porque el comprador no tiene que adivinar qué
          le va a rendir.
        </p>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="yield_factor" className="mb-1.5 block text-sm font-medium">
              Factor de rendimiento
            </label>
            <Input
              id="yield_factor"
              type="number"
              min={80}
              max={130}
              step={0.5}
              placeholder="94"
              error={errors.yield_factor?.message}
              {...register("yield_factor")}
            />
            <p className="mt-1.5 text-xs text-muted-foreground">
              Kilos de pergamino por saco de 70 kg de excelso. Más bajo es mejor; el
              estándar de la Federación es 94.
            </p>
          </div>

          <div>
            <label htmlFor="moisture_pct" className="mb-1.5 block text-sm font-medium">
              Humedad (%)
            </label>
            <Input
              id="moisture_pct"
              type="number"
              min={0}
              max={100}
              step={0.1}
              placeholder="11"
              error={errors.moisture_pct?.message}
              {...register("moisture_pct")}
            />
            <p className="mt-1.5 text-xs text-muted-foreground">
              Entre 10 % y 12 % es el rango seguro para almacenar y trillar.
            </p>
          </div>

          <div>
            <label
              htmlFor="healthy_bean_pct"
              className="mb-1.5 block text-sm font-medium"
            >
              Almendra sana (%)
            </label>
            <Input
              id="healthy_bean_pct"
              type="number"
              min={0}
              max={100}
              step={0.1}
              error={errors.healthy_bean_pct?.message}
              {...register("healthy_bean_pct")}
            />
          </div>

          <div>
            <label htmlFor="pasilla_pct" className="mb-1.5 block text-sm font-medium">
              Pasilla (%)
            </label>
            <Input
              id="pasilla_pct"
              type="number"
              min={0}
              max={100}
              step={0.1}
              error={errors.pasilla_pct?.message}
              {...register("pasilla_pct")}
            />
          </div>

          <div>
            <label
              htmlFor="borer_damage_pct"
              className="mb-1.5 block text-sm font-medium"
            >
              Daño por broca (%)
            </label>
            <Input
              id="borer_damage_pct"
              type="number"
              min={0}
              max={100}
              step={0.1}
              error={errors.borer_damage_pct?.message}
              {...register("borer_damage_pct")}
            />
          </div>

          <div>
            <label htmlFor="screen_sizes" className="mb-1.5 block text-sm font-medium">
              Granulometría
            </label>
            <Input
              id="screen_sizes"
              placeholder="15, 16, 17"
              error={errors.screen_sizes?.message}
              {...register("screen_sizes")}
            />
            <p className="mt-1.5 text-xs text-muted-foreground">
              Mallas en las que se retiene el grano, de la 14 a la 20, separadas por
              comas.
            </p>
          </div>
        </div>
      </fieldset>

      {/* ---------------- Trazabilidad ---------------- */}
      <fieldset className="space-y-4" disabled={isSaving}>
        <legend className="font-display text-lg font-semibold">
          Trazabilidad del lote
        </legend>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="lot_code" className="mb-1.5 block text-sm font-medium">
              Código del lote
            </label>
            <Input
              id="lot_code"
              placeholder="LM-2026-014"
              error={errors.lot_code?.message}
              {...register("lot_code")}
            />
            <p className="mt-1.5 text-xs text-muted-foreground">
              El que usas en tu finca. Permite que una reclamación apunte a este lote y no
              a tu café en general.
            </p>
          </div>

          <div>
            <label htmlFor="sica_code" className="mb-1.5 block text-sm font-medium">
              Código SICA del predio
            </label>
            <Input
              id="sica_code"
              error={errors.sica_code?.message}
              {...register("sica_code")}
            />
            <p className="mt-1.5 text-xs text-muted-foreground">
              Se publica tal como lo escribas: MONK GRAIN no lo verifica ante la
              Federación.
            </p>
          </div>
        </div>

        <div>
          <label htmlFor="notes" className="mb-1.5 block text-sm font-medium">
            Observaciones del lote
          </label>
          <textarea
            id="notes"
            rows={3}
            placeholder="Lo que un comprador debería saber y no cabe en los campos anteriores."
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            {...register("notes")}
          />
        </div>
      </fieldset>

      <div className="flex justify-end gap-3">
        <Button type="submit" disabled={isSaving} aria-busy={isSaving}>
          {isSaving ? "Guardando…" : product ? "Guardar cambios" : "Crear lote"}
        </Button>
      </div>
    </form>
  );
}
