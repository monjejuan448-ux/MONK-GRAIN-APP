"use client";

import { useEffect, useState } from "react";
import { MapPin } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input, Label } from "@/components/ui/input";
import {
  geoApi,
  type Address,
  type AddressInput,
  type GeoItem,
} from "@/features/account/api";
import { ApiError } from "@/lib/api";

/**
 * Formulario de dirección de entrega.
 *
 * El municipio se elige del catálogo oficial y no como texto libre: de él
 * depende el cálculo del envío (HU-CC-03, CA2). El departamento solo sirve para
 * acotar la lista de municipios; no se envía al servidor, que lo deriva del
 * municipio para que no pueda guardarse una combinación imposible.
 */

interface AddressFormProps {
  /** Dirección a editar. Ausente significa que se está creando una nueva. */
  address?: Address;
  /** Verdadero cuando es la primera dirección: se marca predeterminada sola. */
  isFirst?: boolean;
  onSubmit: (data: AddressInput) => Promise<void>;
  onCancel: () => void;
}

const EMPTY_FIELD_ERROR = "Este campo es obligatorio.";

export function AddressForm({ address, isFirst, onSubmit, onCancel }: AddressFormProps) {
  const [departments, setDepartments] = useState<GeoItem[]>([]);
  const [municipalities, setMunicipalities] = useState<GeoItem[]>([]);
  const [departmentId, setDepartmentId] = useState<number | "">(
    address?.department_id ?? "",
  );
  const [municipalityId, setMunicipalityId] = useState<number | "">(
    address?.municipality_id ?? "",
  );

  const [label, setLabel] = useState(address?.label ?? "");
  const [recipientName, setRecipientName] = useState(address?.recipient_name ?? "");
  const [phone, setPhone] = useState(address?.phone ?? "");
  const [streetAddress, setStreetAddress] = useState(address?.street_address ?? "");
  const [neighborhood, setNeighborhood] = useState(address?.neighborhood ?? "");
  const [notes, setNotes] = useState(address?.notes ?? "");
  const [isDefault, setIsDefault] = useState(address?.is_default ?? Boolean(isFirst));

  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isLoadingGeo, setIsLoadingGeo] = useState(true);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const list = await geoApi.departments();
        if (!cancelled) setDepartments(list);
      } catch {
        if (!cancelled) {
          setFormError("No pudimos cargar los departamentos. Recarga la página.");
        }
      } finally {
        if (!cancelled) setIsLoadingGeo(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // Los municipios se piden cada vez que cambia el departamento. Cargar los
  // 1.100 del país de una sola vez haría inmanejable el desplegable.
  useEffect(() => {
    if (departmentId === "") {
      setMunicipalities([]);
      return;
    }
    let cancelled = false;
    void (async () => {
      try {
        const list = await geoApi.municipalities(departmentId);
        if (!cancelled) setMunicipalities(list);
      } catch {
        if (!cancelled) setMunicipalities([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [departmentId]);

  function validate(): boolean {
    const errors: Record<string, string> = {};
    if (recipientName.trim().length < 3) {
      errors.recipient_name = "Escribe el nombre completo de quien recibe.";
    }
    if (phone.trim().length < 7) {
      errors.phone = "Escribe un teléfono de contacto válido.";
    }
    if (departmentId === "") errors.department = EMPTY_FIELD_ERROR;
    if (municipalityId === "") errors.municipality_id = EMPTY_FIELD_ERROR;
    if (streetAddress.trim().length < 5) {
      errors.street_address = "Indica la dirección completa, con número.";
    }
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  }

  async function handleSubmit(event: React.FormEvent): Promise<void> {
    event.preventDefault();
    setFormError(null);
    if (!validate() || municipalityId === "") return;

    setIsSaving(true);
    try {
      await onSubmit({
        // Las cadenas vacías viajan como null: el campo es opcional y guardar
        // "" en lugar de nada obligaría a distinguir los dos casos después.
        label: label.trim() || null,
        recipient_name: recipientName.trim(),
        phone: phone.trim(),
        municipality_id: municipalityId,
        street_address: streetAddress.trim(),
        neighborhood: neighborhood.trim() || null,
        notes: notes.trim() || null,
        is_default: isDefault,
      });
    } catch (error) {
      if (error instanceof ApiError) {
        setFieldErrors(error.fieldErrors);
        setFormError(error.message);
      } else {
        setFormError("No pudimos guardar la dirección. Inténtalo de nuevo.");
      }
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-4">
      <h2 className="flex items-center gap-2 font-display text-lg font-semibold">
        <MapPin className="size-5 text-primary" aria-hidden="true" />
        {address ? "Editar dirección" : "Nueva dirección"}
      </h2>

      {formError && (
        <p
          className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive"
          role="alert"
        >
          {formError}
        </p>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <Label htmlFor="recipient_name" required>
            Quien recibe
          </Label>
          <Input
            id="recipient_name"
            value={recipientName}
            onChange={(event) => setRecipientName(event.target.value)}
            autoComplete="name"
            maxLength={150}
            error={fieldErrors.recipient_name}
          />
        </div>

        <div>
          <Label htmlFor="phone" required>
            Teléfono de contacto
          </Label>
          <Input
            id="phone"
            type="tel"
            inputMode="tel"
            value={phone}
            onChange={(event) => setPhone(event.target.value)}
            autoComplete="tel"
            maxLength={30}
            placeholder="3001234567"
            error={fieldErrors.phone}
          />
        </div>

        <div>
          <Label htmlFor="department" required>
            Departamento
          </Label>
          <select
            id="department"
            value={departmentId}
            disabled={isLoadingGeo}
            onChange={(event) => {
              setDepartmentId(event.target.value ? Number(event.target.value) : "");
              // El municipio elegido pertenece al departamento anterior: dejarlo
              // seleccionado enviaría al servidor una pareja que no existe.
              setMunicipalityId("");
            }}
            aria-invalid={fieldErrors.department ? true : undefined}
            aria-describedby={fieldErrors.department ? "department-error" : undefined}
            className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-50"
          >
            <option value="">{isLoadingGeo ? "Cargando…" : "Selecciona…"}</option>
            {departments.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
          {fieldErrors.department && (
            <p id="department-error" className="mt-1.5 text-sm text-destructive" role="alert">
              {fieldErrors.department}
            </p>
          )}
        </div>

        <div>
          <Label htmlFor="municipality_id" required>
            Municipio
          </Label>
          <select
            id="municipality_id"
            value={municipalityId}
            disabled={departmentId === ""}
            onChange={(event) =>
              setMunicipalityId(event.target.value ? Number(event.target.value) : "")
            }
            aria-invalid={fieldErrors.municipality_id ? true : undefined}
            aria-describedby={
              fieldErrors.municipality_id ? "municipality_id-error" : undefined
            }
            className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-50"
          >
            <option value="">
              {departmentId === "" ? "Elige el departamento primero" : "Selecciona…"}
            </option>
            {municipalities.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
          {fieldErrors.municipality_id && (
            <p
              id="municipality_id-error"
              className="mt-1.5 text-sm text-destructive"
              role="alert"
            >
              {fieldErrors.municipality_id}
            </p>
          )}
        </div>

        <div className="sm:col-span-2">
          <Label htmlFor="street_address" required>
            Dirección
          </Label>
          <Input
            id="street_address"
            value={streetAddress}
            onChange={(event) => setStreetAddress(event.target.value)}
            autoComplete="street-address"
            maxLength={255}
            placeholder="Calle 10 # 5-20, apartamento 302"
            error={fieldErrors.street_address}
          />
        </div>

        <div>
          <Label htmlFor="neighborhood">Barrio</Label>
          <Input
            id="neighborhood"
            value={neighborhood}
            onChange={(event) => setNeighborhood(event.target.value)}
            maxLength={100}
            error={fieldErrors.neighborhood}
          />
        </div>

        <div>
          <Label htmlFor="label">Nombre para reconocerla</Label>
          <Input
            id="label"
            value={label}
            onChange={(event) => setLabel(event.target.value)}
            maxLength={50}
            placeholder="Casa, Oficina, Finca…"
            error={fieldErrors.label}
          />
        </div>

        <div className="sm:col-span-2">
          <Label htmlFor="notes">Indicaciones para la entrega</Label>
          <textarea
            id="notes"
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            rows={2}
            maxLength={500}
            placeholder="Ej. Dejar en portería, timbre 302."
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          />
        </div>
      </div>

      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={isDefault}
          // La primera dirección es forzosamente la predeterminada: permitir
          // desmarcarla dejaría al comprador sin ninguna preseleccionada en el
          // checkout, que es justo el paso que esta pantalla desbloquea.
          disabled={Boolean(isFirst)}
          onChange={(event) => setIsDefault(event.target.checked)}
          className="size-4 rounded border-input accent-primary"
        />
        Usar como dirección predeterminada
      </label>

      <div className="flex flex-wrap gap-3">
        <Button type="submit" isLoading={isSaving}>
          {address ? "Guardar cambios" : "Agregar dirección"}
        </Button>
        <Button type="button" variant="outline" onClick={onCancel} disabled={isSaving}>
          Cancelar
        </Button>
      </div>
    </form>
  );
}
