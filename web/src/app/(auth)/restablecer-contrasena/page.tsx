"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { CheckCircle2, XCircle } from "lucide-react";

import { Skeleton } from "@/components/shared/states";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { authApi } from "@/features/auth/api";
import {
  passwordResetConfirmSchema,
  type PasswordResetConfirmInput,
} from "@/features/auth/schemas";
import { ApiError } from "@/lib/api";

function ResetPasswordContent() {
  const router = useRouter();
  const token = useSearchParams().get("token");

  const [done, setDone] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<PasswordResetConfirmInput>({
    resolver: zodResolver(passwordResetConfirmSchema),
  });

  async function onSubmit(data: PasswordResetConfirmInput) {
    if (!token) return;
    setFormError(null);

    try {
      await authApi.confirmPasswordReset(token, data.password);
      // El backend cierra todas las sesiones al cambiar la contraseña, así que
      // cualquier resto de sesión en este navegador ya no sirve.
      sessionStorage.clear();
      setDone(true);
    } catch (error) {
      setFormError(
        error instanceof ApiError
          ? error.message
          : "No pudimos conectar con el servidor. Inténtalo de nuevo.",
      );
    }
  }

  // El enlace del correo siempre trae el token; sin él no hay nada que hacer.
  if (!token) {
    return (
      <CardContent className="pt-8 text-center">
        <XCircle className="mx-auto mb-4 size-12 text-destructive" aria-hidden="true" />
        <h1 className="font-display text-xl font-semibold">Enlace incompleto</h1>
        <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
          Este enlace no incluye el código de verificación. Copia la dirección completa
          desde el correo o solicita uno nuevo.
        </p>
        <Link
          href="/recuperar-contrasena"
          className="mt-6 inline-block text-sm font-medium text-primary hover:underline"
        >
          Solicitar un enlace nuevo
        </Link>
      </CardContent>
    );
  }

  if (done) {
    return (
      <CardContent className="pt-8 text-center">
        <CheckCircle2 className="mx-auto mb-4 size-12 text-forest" aria-hidden="true" />
        <h1 className="font-display text-xl font-semibold">Contraseña actualizada</h1>
        <p className="mt-3 text-sm leading-relaxed text-muted-foreground" role="status">
          Ya puedes entrar con tu nueva contraseña. Por seguridad cerramos las sesiones
          que tuvieras abiertas en otros dispositivos.
        </p>
        <Button className="mt-6 w-full" onClick={() => router.push("/ingresar")}>
          Iniciar sesión
        </Button>
      </CardContent>
    );
  }

  return (
    <>
      <CardHeader>
        <CardTitle>Crea tu nueva contraseña</CardTitle>
        <CardDescription>
          Debe tener al menos 12 caracteres, con letras y números.
        </CardDescription>
      </CardHeader>

      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          {formError && (
            <div
              role="alert"
              className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive"
            >
              <p>{formError}</p>
              <Link
                href="/recuperar-contrasena"
                className="mt-1 inline-block font-medium underline"
              >
                Solicitar un enlace nuevo
              </Link>
            </div>
          )}

          <div>
            <Label htmlFor="password">Nueva contraseña</Label>
            <Input
              id="password"
              type="password"
              autoComplete="new-password"
              error={errors.password?.message}
              {...register("password")}
            />
          </div>

          <div>
            <Label htmlFor="confirmPassword">Repite la contraseña</Label>
            <Input
              id="confirmPassword"
              type="password"
              autoComplete="new-password"
              error={errors.confirmPassword?.message}
              {...register("confirmPassword")}
            />
          </div>

          <Button
            type="submit"
            className="w-full"
            disabled={isSubmitting}
            aria-busy={isSubmitting}
          >
            {isSubmitting ? "Guardando…" : "Guardar contraseña"}
          </Button>
        </form>
      </CardContent>
    </>
  );
}

export default function ResetPasswordPage() {
  return (
    <Card>
      {/* `useSearchParams` exige un límite de Suspense en el App Router. */}
      <Suspense
        fallback={
          <CardContent className="pt-8">
            <Skeleton className="mx-auto h-6 w-48" />
          </CardContent>
        }
      >
        <ResetPasswordContent />
      </Suspense>
    </Card>
  );
}
