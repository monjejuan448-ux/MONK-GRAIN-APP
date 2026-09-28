"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import { ArrowLeft, MapPin, Pencil, Plus, Star, Trash2 } from "lucide-react";

import { EmptyState, ErrorState, Skeleton } from "@/components/shared/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  addressesApi,
  geoApi,
  type Address,
  type AddressInput,
} from "@/features/account/api";
import { AddressForm } from "@/features/account/components/AddressForm";
import { ApiError } from "@/lib/api";
import { session } from "@/lib/session";

/**
 * Direcciones de entrega del comprador (HU-CC-03).
 *
 * Es la pantalla que el checkout necesita: sin una dirección registrada no hay
 * pedido posible, y hasta ahora no existía ningún lugar donde crearla. Por eso,
 * cuando se llega aquí sin ninguna, el formulario aparece abierto en vez de
 * exigir un clic más.
 */

type Editing = { mode: "none" } | { mode: "new" } | { mode: "edit"; address: Address };

function AddressesContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  // El checkout manda aquí con `?volver=checkout` para poder devolver al
  // comprador al punto exacto donde se quedó.
  const returnTo = searchParams.get("volver") === "checkout" ? "/checkout" : null;

  const [addresses, setAddresses] = useState<Address[]>([]);
  const [placeNames, setPlaceNames] = useState<Record<number, string>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(false);
  const [editing, setEditing] = useState<Editing>({ mode: "none" });
  const [actionError, setActionError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  /** Resuelve los nombres de municipio y departamento de las direcciones.
   *
   * La API devuelve identificadores, no nombres: se piden los municipios de los
   * departamentos que realmente aparecen, en lugar de los del país entero. */
  const loadPlaceNames = useCallback(async (list: Address[]) => {
    const departmentIds = [...new Set(list.map((item) => item.department_id))];
    if (departmentIds.length === 0) return;

    try {
      const departments = await geoApi.departments();
      const names: Record<number, string> = {};
      for (const department of departments) {
        names[department.id] = department.name;
      }

      const groups = await Promise.all(
        departmentIds.map((id) => geoApi.municipalities(id).catch(() => [])),
      );
      for (const group of groups) {
        for (const municipality of group) {
          names[municipality.id] = municipality.name;
        }
      }
      setPlaceNames(names);
    } catch {
      // Sin los nombres la pantalla sigue siendo utilizable: se omite la línea
      // de ubicación en lugar de dejar la lista entera en estado de error.
    }
  }, []);

  const load = useCallback(async () => {
    const token = session.getAccessToken();
    if (!token) {
      router.push("/ingresar");
      return;
    }

    setError(false);
    try {
      const list = await addressesApi.list(token);
      setAddresses(list);
      // Sin ninguna dirección, el formulario se abre solo: llegar a una pantalla
      // vacía desde un checkout bloqueado y tener que buscar el botón sería
      // hacer más largo justo el camino que aquí se viene a desatascar.
      setEditing(list.length === 0 ? { mode: "new" } : { mode: "none" });
      void loadPlaceNames(list);
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.isUnauthorized) {
        router.push("/ingresar");
        return;
      }
      setError(true);
    } finally {
      setIsLoading(false);
    }
  }, [router, loadPlaceNames]);

  useEffect(() => {
    void load();
  }, [load]);

  function locationOf(address: Address): string | null {
    const municipality = placeNames[address.municipality_id];
    const department = placeNames[address.department_id];
    if (!municipality && !department) return null;
    return [municipality, department].filter(Boolean).join(", ");
  }

  async function handleCreate(data: AddressInput): Promise<void> {
    const token = session.getAccessToken();
    if (!token) {
      router.push("/ingresar");
      return;
    }
    await addressesApi.create(token, data);
    setNotice("Dirección agregada.");
    setActionError(null);
    await load();
    // Si se llegó desde un checkout sin direcciones, se vuelve a él: ya hay con
    // qué completar la compra.
    if (returnTo) router.push(returnTo);
  }

  async function handleUpdate(addressId: string, data: AddressInput): Promise<void> {
    const token = session.getAccessToken();
    if (!token) {
      router.push("/ingresar");
      return;
    }
    await addressesApi.update(token, addressId, data);
    setNotice("Dirección actualizada.");
    setActionError(null);
    await load();
  }

  async function handleMakeDefault(addressId: string): Promise<void> {
    const token = session.getAccessToken();
    if (!token) return;
    setBusyId(addressId);
    setActionError(null);
    try {
      await addressesApi.makeDefault(token, addressId);
      setNotice("Dirección predeterminada actualizada.");
      await load();
    } catch (requestError) {
      setActionError(
        requestError instanceof ApiError
          ? requestError.message
          : "No pudimos cambiar la dirección predeterminada.",
      );
    } finally {
      setBusyId(null);
    }
  }

  async function handleDelete(address: Address): Promise<void> {
    const token = session.getAccessToken();
    if (!token) return;
    const name = address.label ?? address.street_address;
    if (!window.confirm(`¿Eliminar la dirección «${name}»?`)) return;

    setBusyId(address.id);
    setActionError(null);
    try {
      await addressesApi.remove(token, address.id);
      setNotice("Dirección eliminada.");
      await load();
    } catch (requestError) {
      setActionError(
        requestError instanceof ApiError
          ? requestError.message
          : "No pudimos eliminar la dirección.",
      );
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <Link
        href="/mi-cuenta"
        className="mb-6 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
        Volver a mi cuenta
      </Link>

      <h1 className="font-display text-3xl font-bold">Mis direcciones</h1>
      <p className="mb-8 mt-1 text-muted-foreground">
        La dirección predeterminada es la que el checkout propone primero. Cada pedido
        guarda su propia copia, así que corregir una dirección aquí no altera lo que ya
        se despachó.
      </p>

      {returnTo && (
        <p
          className="mb-6 rounded-md border border-primary/30 bg-primary/5 px-4 py-3 text-sm"
          role="status"
        >
          Agrega una dirección para poder completar tu compra. Al guardarla te devolvemos
          al checkout.
        </p>
      )}

      {/* Las confirmaciones y los errores se anuncian, no solo se pintan. */}
      <div aria-live="polite" className="sr-only">
        {notice}
      </div>

      {actionError && (
        <p
          className="mb-6 rounded-md border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive"
          role="alert"
        >
          {actionError}
        </p>
      )}

      {isLoading && <Skeleton className="h-48 w-full" />}
      {!isLoading && error && <ErrorState onRetry={() => void load()} />}

      {!isLoading && !error && (
        <div className="space-y-6">
          {addresses.length > 0 && (
            <ul className="space-y-4">
              {addresses.map((address) =>
                editing.mode === "edit" && editing.address.id === address.id ? (
                  <li key={address.id}>
                    <Card>
                      <CardContent className="pt-6">
                        <AddressForm
                          address={address}
                          onSubmit={(data) => handleUpdate(address.id, data)}
                          onCancel={() => setEditing({ mode: "none" })}
                        />
                      </CardContent>
                    </Card>
                  </li>
                ) : (
                  <li key={address.id}>
                    <Card>
                      <CardContent className="pt-6">
                        <div className="flex flex-wrap items-start justify-between gap-4">
                          <div className="min-w-0">
                            <div className="flex flex-wrap items-center gap-2">
                              <MapPin
                                className="size-4 shrink-0 text-primary"
                                aria-hidden="true"
                              />
                              <span className="font-display font-semibold">
                                {address.label ?? "Dirección de entrega"}
                              </span>
                              {address.is_default && (
                                <Badge variant="primary">Predeterminada</Badge>
                              )}
                            </div>
                            <p className="mt-2 text-sm">
                              {address.street_address}
                              {address.neighborhood && `, ${address.neighborhood}`}
                            </p>
                            {locationOf(address) && (
                              <p className="text-sm text-muted-foreground">
                                {locationOf(address)}
                              </p>
                            )}
                            <p className="mt-1 text-sm text-muted-foreground">
                              {address.recipient_name} · Tel. {address.phone}
                            </p>
                            {address.notes && (
                              <p className="mt-1 text-sm italic text-muted-foreground">
                                {address.notes}
                              </p>
                            )}
                          </div>

                          <div className="flex shrink-0 flex-wrap gap-2">
                            {!address.is_default && (
                              <Button
                                variant="ghost"
                                size="sm"
                                disabled={busyId === address.id}
                                onClick={() => void handleMakeDefault(address.id)}
                              >
                                <Star className="size-4" aria-hidden="true" />
                                Predeterminada
                              </Button>
                            )}
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => setEditing({ mode: "edit", address })}
                            >
                              <Pencil className="size-4" aria-hidden="true" />
                              Editar
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-destructive hover:bg-destructive/10"
                              disabled={busyId === address.id}
                              onClick={() => void handleDelete(address)}
                            >
                              <Trash2 className="size-4" aria-hidden="true" />
                              <span className="sr-only sm:not-sr-only">Eliminar</span>
                            </Button>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </li>
                ),
              )}
            </ul>
          )}

          {editing.mode === "new" ? (
            <Card>
              <CardContent className="pt-6">
                <AddressForm
                  isFirst={addresses.length === 0}
                  onSubmit={handleCreate}
                  onCancel={() =>
                    // Sin ninguna dirección no hay nada a lo que volver: se deja
                    // el formulario abierto en vez de mostrar una pantalla vacía.
                    addresses.length > 0 ? setEditing({ mode: "none" }) : undefined
                  }
                />
              </CardContent>
            </Card>
          ) : (
            addresses.length > 0 &&
            editing.mode === "none" && (
              <Button variant="outline" onClick={() => setEditing({ mode: "new" })}>
                <Plus className="size-4" aria-hidden="true" />
                Agregar otra dirección
              </Button>
            )
          )}

          {addresses.length === 0 && editing.mode === "none" && (
            <EmptyState
              icon={<MapPin className="size-10" aria-hidden="true" />}
              title="No tienes direcciones registradas"
              description="Necesitas al menos una para recibir tus pedidos."
              action={
                <Button onClick={() => setEditing({ mode: "new" })}>
                  <Plus className="size-4" aria-hidden="true" />
                  Agregar dirección
                </Button>
              }
            />
          )}
        </div>
      )}
    </div>
  );
}

export default function AddressesPage() {
  // `useSearchParams` obliga a un límite de Suspense en el App Router.
  return (
    <Suspense fallback={<Skeleton className="mx-auto mt-10 h-48 max-w-3xl" />}>
      <AddressesContent />
    </Suspense>
  );
}
