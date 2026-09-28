"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  COFFEE_STATE_OPTIONS,
  PROCESS_OPTIONS,
  ROAST_OPTIONS,
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
      .min(20, "Describe tu café con al menos 20 caracteres.")
      .max(5000),
    state: z.enum(["green", "roasted", "ground"]),
    // Los campos numéricos se validan como texto porque eso es lo que entrega
    // un formulario HTML; convertirlos antes de tiempo convierte un campo vacío
    // en cero, que aquí significaría «gratis».
    base_price: z
      .string()
      .min(1, "Indica el precio.")
      .refine((value) => Number(value) > 0, "El precio debe ser mayor que cero."),
    wholesale_price: z.string().optional(),
    dispatch_days: z
      .string()
      .refine((value) => Number(value) >= 1 && Number(value) <= 30, "Entre 1 y 30 días."),
    storage_conditions: z.string().max(1000).optional(),
    allows_samples: z.boolean(),
    variety: z.string().max(100).optional(),
    process: z.string().optional(),
    roast: z.string().optional(),
    altitude_masl: optionalNumber(3000, "La altitud debe estar entre 0 y 3000 m."),
    cupping_score: optionalNumber(100, "El puntaje va de 0 a 100."),
    sensory_profile: z.string().max(2000).optional(),
    tasting_notes: z.string().max(300).optional(),
    harvest_date: z.string().optional(),
  })
  .refine(
    (data) =>
      !data.wholesale_price || Number(data.wholesale_price) < Number(data.base_price),
    {
      message: "El precio mayorista debe ser menor que el precio al detal.",
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
      state: product?.state ?? "roasted",
      base_price: product?.base_price ?? "",
      wholesale_price: product?.wholesale_price ?? "",
      dispatch_days: String(product?.dispatch_days ?? 3),
      storage_conditions: product?.storage_conditions ?? "",
      allows_samples: product?.allows_samples ?? false,
      variety: attributes?.variety ?? "",
      process: attributes?.process ?? "",
      roast: attributes?.roast ?? "",
      altitude_masl: attributes?.altitude_masl ? String(attributes.altitude_masl) : "",
      cupping_score: attributes?.cupping_score ?? "",
      sensory_profile: attributes?.sensory_profile ?? "",
      tasting_notes: attributes?.tasting_notes?.join(", ") ?? "",
      harvest_date: attributes?.harvest_date ?? "",
    },
  });

  const submit = handleSubmit(async (values) => {
    await onSubmit({
      name: values.name.trim(),
      description: values.description.trim(),
      state: values.state,
      base_price: values.base_price,
      wholesale_price: orNull(values.wholesale_price),
      dispatch_days: Number(values.dispatch_days),
      storage_conditions: orNull(values.storage_conditions),
      allows_samples: Boolean(values.allows_samples),
      attributes: {
        variety: orNull(values.variety),
        process: orNull(values.process),
        roast: orNull(values.roast),
        altitude_masl: values.altitude_masl === "" ? null : Number(values.altitude_masl),
        cupping_score: orNull(values.cupping_score),
        sensory_profile: orNull(values.sensory_profile),
        harvest_date: orNull(values.harvest_date),
        tasting_notes: values.tasting_notes
          ? values.tasting_notes
              .split(",")
              .map((note) => note.trim())
              .filter(Boolean)
              .slice(0, 10)
          : null,
      },
    });
  });

  return (
    <form onSubmit={submit} className="space-y-8" noValidate>
      <fieldset className="space-y-4" disabled={isSaving}>
        <legend className="font-display text-lg font-semibold">Tu café</legend>

        <div>
          <label htmlFor="name" className="mb-1.5 block text-sm font-medium">
            Nombre del café <span aria-hidden="true">*</span>
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
            placeholder="Cuenta su origen, cómo se procesa y a qué sabe."
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
            <label htmlFor="state" className="mb-1.5 block text-sm font-medium">
              Presentación <span aria-hidden="true">*</span>
            </label>
            <select
              id="state"
              className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm"
              {...register("state")}
            >
              {COFFEE_STATE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

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
              Precio al detal (COP) <span aria-hidden="true">*</span>
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
              Precio mayorista (opcional)
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
        <legend className="font-display text-lg font-semibold">Origen y catación</legend>
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
            <label htmlFor="roast" className="mb-1.5 block text-sm font-medium">
              Nivel de tueste
            </label>
            <select
              id="roast"
              className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm"
              {...register("roast")}
            >
              <option value="">Sin especificar</option>
              {ROAST_OPTIONS.map((option) => (
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
            <label htmlFor="cupping_score" className="mb-1.5 block text-sm font-medium">
              Puntaje de catación (SCA)
            </label>
            <Input
              id="cupping_score"
              type="number"
              min={0}
              max={100}
              step={0.25}
              error={errors.cupping_score?.message}
              {...register("cupping_score")}
            />
          </div>

          <div>
            <label htmlFor="harvest_date" className="mb-1.5 block text-sm font-medium">
              Fecha de cosecha
            </label>
            <Input id="harvest_date" type="date" {...register("harvest_date")} />
          </div>
        </div>

        <div>
          <label htmlFor="tasting_notes" className="mb-1.5 block text-sm font-medium">
            Notas de cata
          </label>
          <Input
            id="tasting_notes"
            placeholder="panela, mandarina, chocolate"
            {...register("tasting_notes")}
          />
          <p className="mt-1.5 text-xs text-muted-foreground">
            Sepáralas con comas, hasta 10.
          </p>
        </div>

        <div>
          <label htmlFor="sensory_profile" className="mb-1.5 block text-sm font-medium">
            Perfil sensorial
          </label>
          <textarea
            id="sensory_profile"
            rows={3}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            {...register("sensory_profile")}
          />
        </div>

        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" className="size-4" {...register("allows_samples")} />
          Acepto solicitudes de muestra de compradores empresariales
        </label>
      </fieldset>

      <div className="flex justify-end gap-3">
        <Button type="submit" disabled={isSaving} aria-busy={isSaving}>
          {isSaving ? "Guardando…" : product ? "Guardar cambios" : "Crear café"}
        </Button>
      </div>
    </form>
  );
}
