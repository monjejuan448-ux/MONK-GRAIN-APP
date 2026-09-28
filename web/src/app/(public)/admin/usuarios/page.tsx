"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Search, ShieldOff, ShieldCheck, Users } from "lucide-react";

import { EmptyState, ErrorState, Skeleton } from "@/components/shared/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import {
  adminApi,
  ROLE_LABELS,
  USER_STATUS_META,
  type AdminUserItem,
} from "@/features/dashboard/api";
import { ApiError } from "@/lib/api";
import { formatDateShort } from "@/lib/format";
import { session } from "@/lib/session";
import { cn } from "@/lib/utils";

/**
 * Cuentas de la plataforma, para poder encontrar la que se va a suspender.
 *
 * El endpoint de suspensión existía desde el principio, pero no había listado ni
 * búsqueda: para usarlo había que conocer el identificador de la cuenta de
 * memoria, de modo que en la práctica era inalcanzable.
 *
 * Suspender deja fuera a una persona de inmediato —el usuario se recarga en cada
 * petición, no se espera a que expire su token—, así que el motivo se pide antes
 * y queda en la auditoría.
 */

const STATUS_FILTERS = [
  { value: "", label: "Todas" },
  { value: "active", label: "Activas" },
  { value: "suspended", label: "Suspendidas" },
  { value: "pending_verification", label: "Sin verificar" },
];

const ROLE_FILTERS = [
  { value: "", label: "Cualquier rol" },
  { value: "consumer", label: "Compradores" },
  { value: "business", label: "Empresas" },
  { value: "producer", label: "Vendedores" },
  { value: "admin", label: "Administración" },
];

export default function AdminUsersPage() {
  const router = useRouter();
  const [users, setUsers] = useState<AdminUserItem[]>([]);
  const [total, setTotal] = useState(0);
  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [roleFilter, setRoleFilter] = useState("");

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(false);
  const [forbidden, setForbidden] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [suspendingId, setSuspendingId] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    const token = session.getAccessToken();
    if (!token) {
      router.push("/ingresar");
      return;
    }

    setError(false);
    try {
      const page = await adminApi.users(token, {
        q: submittedQuery || undefined,
        status: statusFilter || undefined,
        role: roleFilter || undefined,
      });
      setUsers(page.items);
      setTotal(page.total);
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.isUnauthorized) {
        router.push("/ingresar");
        return;
      }
      if (requestError instanceof ApiError && requestError.status === 403) {
        setForbidden(true);
        return;
      }
      setError(true);
    } finally {
      setIsLoading(false);
    }
  }, [router, submittedQuery, statusFilter, roleFilter]);

  useEffect(() => {
    void load();
  }, [load]);

  async function toggle(user: AdminUserItem, suspend: boolean): Promise<void> {
    const token = session.getAccessToken();
    if (!token) return;

    setBusyId(user.id);
    setActionError(null);
    try {
      await adminApi.suspendUser(
        token,
        user.id,
        suspend,
        suspend ? reason.trim() : undefined,
      );
      setNotice(
        suspend
          ? `La cuenta de ${user.email} quedó suspendida.`
          : `La cuenta de ${user.email} volvió a estar activa.`,
      );
      setSuspendingId(null);
      setReason("");
      await load();
    } catch (requestError) {
      setActionError(
        requestError instanceof ApiError
          ? requestError.message
          : "No pudimos cambiar el estado de la cuenta.",
      );
    } finally {
      setBusyId(null);
    }
  }

  if (forbidden) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-16">
        <EmptyState
          icon={<Users className="size-10" aria-hidden="true" />}
          title="Esta sección es de administración"
          description="Tu cuenta no tiene ese rol."
        />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      <Link
        href="/admin"
        className="mb-6 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
        Volver al panel
      </Link>

      <h1 className="font-display text-3xl font-bold">Cuentas</h1>
      <p className="mb-6 mt-1 text-muted-foreground">
        Suspender una cuenta la deja fuera de inmediato, sin esperar a que caduque su
        sesión. Cada suspensión queda en el registro de auditoría con quién la ordenó.
      </p>

      <div aria-live="polite" className="sr-only">
        {notice}
      </div>

      {/* ---------------- Búsqueda ---------------- */}
      <form
        onSubmit={(event) => {
          event.preventDefault();
          setSubmittedQuery(query.trim());
        }}
        className="mb-4 flex flex-wrap gap-2"
      >
        <div className="min-w-56 flex-1">
          <Label htmlFor="q" className="sr-only">
            Buscar por correo o nombre
          </Label>
          <Input
            id="q"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Buscar por correo o nombre"
            maxLength={120}
          />
        </div>
        <Button type="submit" variant="outline">
          <Search className="size-4" aria-hidden="true" />
          Buscar
        </Button>
      </form>

      <div className="mb-6 flex flex-wrap gap-4">
        <FilterRow
          label="Estado"
          options={STATUS_FILTERS}
          selected={statusFilter}
          onSelect={setStatusFilter}
        />
        <FilterRow
          label="Rol"
          options={ROLE_FILTERS}
          selected={roleFilter}
          onSelect={setRoleFilter}
        />
      </div>

      {actionError && (
        <p
          className="mb-6 rounded-md border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive"
          role="alert"
        >
          {actionError}
        </p>
      )}

      {isLoading && <Skeleton className="h-64 w-full" />}
      {!isLoading && error && <ErrorState onRetry={() => void load()} />}

      {!isLoading && !error && users.length === 0 && (
        <EmptyState
          icon={<Users className="size-10" aria-hidden="true" />}
          title="Ninguna cuenta coincide"
          description="Prueba con otro texto o quita los filtros."
        />
      )}

      {!isLoading && !error && users.length > 0 && (
        <>
          <p className="mb-3 text-sm text-muted-foreground">
            {total} {total === 1 ? "cuenta" : "cuentas"}
          </p>
          <ul className="space-y-3">
            {users.map((user) => {
              const meta = USER_STATUS_META[user.status];
              const isSuspended = user.status === "suspended";

              return (
                <li key={user.id}>
                  <Card>
                    <CardContent className="pt-6">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="font-medium">{user.full_name}</p>
                          <p className="text-sm text-muted-foreground">{user.email}</p>
                          <p className="mt-1.5 flex flex-wrap items-center gap-1.5">
                            {user.roles.map((role) => (
                              <Badge key={role} variant="outline">
                                {ROLE_LABELS[role] ?? role}
                              </Badge>
                            ))}
                            {user.is_producer && user.producer_status !== "approved" && (
                              <Badge variant="warning">
                                Vendedor {user.producer_status}
                              </Badge>
                            )}
                          </p>
                          <p className="mt-1.5 text-xs text-muted-foreground">
                            Registrada el {formatDateShort(user.created_at)} ·{" "}
                            {user.order_count === 0
                              ? "sin pedidos"
                              : user.order_count === 1
                                ? "1 pedido"
                                : `${user.order_count} pedidos`}
                            {user.last_login_at &&
                              ` · último ingreso ${formatDateShort(user.last_login_at)}`}
                          </p>
                        </div>

                        <div className="flex shrink-0 flex-col items-end gap-2">
                          <Badge variant={meta.variant}>{meta.label}</Badge>
                          {isSuspended ? (
                            <Button
                              size="sm"
                              variant="outline"
                              disabled={busyId === user.id}
                              onClick={() => void toggle(user, false)}
                            >
                              <ShieldCheck className="size-4" aria-hidden="true" />
                              Reactivar
                            </Button>
                          ) : (
                            suspendingId !== user.id && (
                              <Button
                                size="sm"
                                variant="ghost"
                                className="text-destructive hover:bg-destructive/10"
                                disabled={busyId === user.id}
                                onClick={() => {
                                  setSuspendingId(user.id);
                                  setReason("");
                                  setActionError(null);
                                }}
                              >
                                <ShieldOff className="size-4" aria-hidden="true" />
                                Suspender
                              </Button>
                            )
                          )}
                        </div>
                      </div>

                      {suspendingId === user.id && (
                        <div className="mt-4 space-y-3 border-t border-border pt-4">
                          <div>
                            <Label htmlFor={`reason-${user.id}`}>
                              Motivo de la suspensión
                            </Label>
                            <textarea
                              id={`reason-${user.id}`}
                              value={reason}
                              onChange={(event) => setReason(event.target.value)}
                              rows={2}
                              maxLength={500}
                              placeholder="Queda en el registro de auditoría."
                              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                            />
                          </div>
                          <div className="flex flex-wrap gap-2">
                            <Button
                              size="sm"
                              variant="destructive"
                              disabled={busyId === user.id}
                              onClick={() => void toggle(user, true)}
                            >
                              Confirmar la suspensión
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => setSuspendingId(null)}
                            >
                              Volver
                            </Button>
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </li>
              );
            })}
          </ul>
        </>
      )}
    </div>
  );
}

function FilterRow({
  label,
  options,
  selected,
  onSelect,
}: {
  label: string;
  options: Array<{ value: string; label: string }>;
  selected: string;
  onSelect: (value: string) => void;
}) {
  return (
    <div role="group" aria-label={label}>
      <p className="mb-1.5 text-xs font-medium text-muted-foreground">{label}</p>
      <div className="flex flex-wrap gap-2">
        {options.map((option) => (
          <button
            key={option.value}
            type="button"
            aria-pressed={selected === option.value}
            onClick={() => onSelect(option.value)}
            className={cn(
              "rounded-full border px-3 py-1 text-xs transition-colors",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
              selected === option.value
                ? "border-primary bg-primary text-primary-foreground"
                : "border-border hover:bg-muted",
            )}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  );
}
