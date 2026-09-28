"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, KeyRound, MapPin, UserRound } from "lucide-react";

import { ErrorState, Skeleton } from "@/components/shared/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { profileApi } from "@/features/account/api";
import { authApi, type CurrentUser } from "@/features/auth/api";
import { ApiError } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { session } from "@/lib/session";

/**
 * Datos personales del titular (HU-CC-02).
 *
 * El panel de la cuenta enlazaba aquí desde el principio, a una ruta que no
 * existía. El correo se muestra pero no se edita: cambiarlo obliga a verificarlo
 * de nuevo, porque es por donde se recupera la contraseña.
 */

export default function ProfilePage() {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(false);

  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [notifications, setNotifications] = useState(true);
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [profileFieldErrors, setProfileFieldErrors] = useState<Record<string, string>>(
    {},
  );

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [repeatPassword, setRepeatPassword] = useState("");
  const [isSavingPassword, setIsSavingPassword] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);

  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    const token = session.getAccessToken();
    if (!token) {
      router.push("/ingresar");
      return;
    }

    setError(false);
    try {
      const current = await authApi.me(token);
      setUser(current);
      setFullName(current.full_name);
      setPhone(current.phone ?? "");
      setNotifications(current.email_notifications_enabled);
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

  async function handleProfileSubmit(event: React.FormEvent): Promise<void> {
    event.preventDefault();
    const token = session.getAccessToken();
    if (!token) {
      router.push("/ingresar");
      return;
    }

    setProfileError(null);
    setProfileFieldErrors({});
    if (fullName.trim().length < 3) {
      setProfileFieldErrors({ full_name: "Escribe tu nombre completo." });
      return;
    }

    setIsSavingProfile(true);
    try {
      const updated = await profileApi.update(token, {
        full_name: fullName.trim(),
        // Vacío significa borrarlo: el teléfono es opcional.
        phone: phone.trim() || null,
        email_notifications_enabled: notifications,
      });
      setNotice("Datos actualizados.");
      setUser((current) => (current ? { ...current, ...updated } : current));
    } catch (requestError) {
      if (requestError instanceof ApiError) {
        setProfileFieldErrors(requestError.fieldErrors);
        setProfileError(requestError.message);
      } else {
        setProfileError("No pudimos guardar los cambios. Inténtalo de nuevo.");
      }
    } finally {
      setIsSavingProfile(false);
    }
  }

  async function handlePasswordSubmit(event: React.FormEvent): Promise<void> {
    event.preventDefault();
    const token = session.getAccessToken();
    if (!token) {
      router.push("/ingresar");
      return;
    }

    setPasswordError(null);
    if (newPassword !== repeatPassword) {
      setPasswordError("Las dos contraseñas nuevas no coinciden.");
      return;
    }

    setIsSavingPassword(true);
    try {
      await authApi.changePassword(token, currentPassword, newPassword);
      setNotice("Contraseña cambiada.");
      setCurrentPassword("");
      setNewPassword("");
      setRepeatPassword("");
    } catch (requestError) {
      setPasswordError(
        requestError instanceof ApiError
          ? requestError.message
          : "No pudimos cambiar la contraseña. Inténtalo de nuevo.",
      );
    } finally {
      setIsSavingPassword(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <Link
        href="/mi-cuenta"
        className="mb-6 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
        Volver a mi cuenta
      </Link>

      <h1 className="font-display text-3xl font-bold">Mis datos</h1>
      <p className="mb-8 mt-1 text-muted-foreground">
        Tus datos personales y tu contraseña. Las direcciones de entrega se gestionan
        aparte.
      </p>

      <div aria-live="polite" className="sr-only">
        {notice}
      </div>

      {isLoading && <Skeleton className="h-64 w-full" />}
      {!isLoading && error && <ErrorState onRetry={() => void load()} />}

      {!isLoading && !error && user && (
        <div className="space-y-6">
          {/* ---------------- Datos personales ---------------- */}
          <Card>
            <CardContent className="pt-6">
              <form onSubmit={handleProfileSubmit} noValidate className="space-y-4">
                <h2 className="flex items-center gap-2 font-display text-lg font-semibold">
                  <UserRound className="size-5 text-primary" aria-hidden="true" />
                  Datos personales
                </h2>

                {profileError && (
                  <p className="text-sm text-destructive" role="alert">
                    {profileError}
                  </p>
                )}

                <div>
                  <Label htmlFor="email">Correo electrónico</Label>
                  {/* Solo lectura: cambiarlo exige verificarlo de nuevo. */}
                  <Input id="email" value={user.email} readOnly disabled />
                  <p className="mt-1.5 text-xs text-muted-foreground">
                    Para cambiar tu correo escríbenos: hay que verificar el nuevo antes de
                    usarlo, porque es por donde se recupera la contraseña.
                  </p>
                </div>

                <div>
                  <Label htmlFor="full_name" required>
                    Nombre completo
                  </Label>
                  <Input
                    id="full_name"
                    value={fullName}
                    onChange={(event) => setFullName(event.target.value)}
                    autoComplete="name"
                    maxLength={150}
                    error={profileFieldErrors.full_name}
                  />
                </div>

                <div>
                  <Label htmlFor="phone">Teléfono</Label>
                  <Input
                    id="phone"
                    type="tel"
                    inputMode="tel"
                    value={phone}
                    onChange={(event) => setPhone(event.target.value)}
                    autoComplete="tel"
                    maxLength={30}
                    error={profileFieldErrors.phone}
                  />
                </div>

                <label className="flex items-start gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={notifications}
                    onChange={(event) => setNotifications(event.target.checked)}
                    className="mt-0.5 size-4 rounded border-input accent-primary"
                  />
                  <span>
                    Quiero recibir avisos por correo sobre mis pedidos.
                    <span className="block text-xs text-muted-foreground">
                      Los correos de seguridad —verificación y cambio de contraseña— se
                      envían siempre.
                    </span>
                  </span>
                </label>

                <Button type="submit" isLoading={isSavingProfile}>
                  Guardar cambios
                </Button>
              </form>
            </CardContent>
          </Card>

          {/* ---------------- Contraseña ---------------- */}
          <Card>
            <CardContent className="pt-6">
              <form onSubmit={handlePasswordSubmit} noValidate className="space-y-4">
                <h2 className="flex items-center gap-2 font-display text-lg font-semibold">
                  <KeyRound className="size-5 text-primary" aria-hidden="true" />
                  Cambiar la contraseña
                </h2>

                {passwordError && (
                  <p className="text-sm text-destructive" role="alert">
                    {passwordError}
                  </p>
                )}

                <div>
                  <Label htmlFor="current_password" required>
                    Contraseña actual
                  </Label>
                  <Input
                    id="current_password"
                    type="password"
                    value={currentPassword}
                    onChange={(event) => setCurrentPassword(event.target.value)}
                    autoComplete="current-password"
                    maxLength={128}
                  />
                </div>

                <div>
                  <Label htmlFor="new_password" required>
                    Contraseña nueva
                  </Label>
                  <Input
                    id="new_password"
                    type="password"
                    value={newPassword}
                    onChange={(event) => setNewPassword(event.target.value)}
                    autoComplete="new-password"
                    maxLength={128}
                  />
                  <p className="mt-1.5 text-xs text-muted-foreground">
                    Al menos 12 caracteres, con mayúscula, minúscula y número.
                  </p>
                </div>

                <div>
                  <Label htmlFor="repeat_password" required>
                    Repite la contraseña nueva
                  </Label>
                  <Input
                    id="repeat_password"
                    type="password"
                    value={repeatPassword}
                    onChange={(event) => setRepeatPassword(event.target.value)}
                    autoComplete="new-password"
                    maxLength={128}
                  />
                </div>

                <Button type="submit" variant="outline" isLoading={isSavingPassword}>
                  Cambiar la contraseña
                </Button>
              </form>
            </CardContent>
          </Card>

          {/* ---------------- Resumen de la cuenta ---------------- */}
          <Card>
            <CardContent className="space-y-3 pt-6">
              <h2 className="font-display text-lg font-semibold">Tu cuenta</h2>
              <p className="text-sm text-muted-foreground">
                Registrada el {formatDate(user.created_at)}.
              </p>
              <div className="flex flex-wrap gap-2">
                {user.roles.map((role) => (
                  <Badge key={role.code} variant="outline">
                    {role.name}
                  </Badge>
                ))}
              </div>
              <Link
                href="/mi-cuenta/direcciones"
                className="inline-flex items-center gap-1.5 text-sm text-primary hover:underline"
              >
                <MapPin className="size-4" aria-hidden="true" />
                Gestionar mis direcciones de entrega
              </Link>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
