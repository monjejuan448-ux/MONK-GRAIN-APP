"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";

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
import { loginSchema, type LoginInput } from "@/features/auth/schemas";
import { ApiError } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [formError, setFormError] = useState<string | null>(null);
  const [needsVerification, setNeedsVerification] = useState(false);

  const {
    register,
    handleSubmit,
    getValues,
    formState: { errors, isSubmitting },
  } = useForm<LoginInput>({ resolver: zodResolver(loginSchema) });

  async function onSubmit(data: LoginInput) {
    setFormError(null);
    setNeedsVerification(false);

    try {
      const tokens = await authApi.login(data);
      // Almacenamiento provisional hasta que la fase 9 introduzca el proveedor
      // de sesión con cookies httpOnly.
      sessionStorage.setItem("mg_access_token", tokens.access_token);
      sessionStorage.setItem("mg_refresh_token", tokens.refresh_token);
      router.push("/");
    } catch (error) {
      if (error instanceof ApiError) {
        setFormError(error.message);
        // El backend distingue este caso para poder ofrecer el reenvío.
        if (error.message.includes("verificar tu correo")) setNeedsVerification(true);
      } else {
        setFormError("No pudimos conectar con el servidor. Inténtalo de nuevo.");
      }
    }
  }

  async function resendVerification() {
    const email = getValues("email");
    if (!email) return;
    await authApi.resendVerification(email).catch(() => null);
    setFormError("Si la cuenta existe y está pendiente, enviamos un nuevo enlace.");
    setNeedsVerification(false);
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-2xl">Iniciar sesión</CardTitle>
        <CardDescription>Accede a tu cuenta de MONK GRAIN.</CardDescription>
      </CardHeader>

      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} noValidate>
          {formError && (
            <div
              className="mb-5 rounded-md border border-destructive/30 bg-destructive/5 px-4 py-3"
              role="alert"
            >
              <p className="text-sm text-destructive">{formError}</p>
              {needsVerification && (
                <button
                  type="button"
                  onClick={resendVerification}
                  className="mt-2 text-sm font-medium text-primary underline"
                >
                  Reenviar el enlace de verificación
                </button>
              )}
            </div>
          )}

          <div className="mb-4">
            <Label htmlFor="email" required>
              Correo electrónico
            </Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              placeholder="tu@correo.com"
              error={errors.email?.message}
              {...register("email")}
            />
          </div>

          <div className="mb-2">
            <Label htmlFor="password" required>
              Contraseña
            </Label>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              error={errors.password?.message}
              {...register("password")}
            />
          </div>

          <div className="mb-6 text-right">
            <Link
              href="/recuperar-contrasena"
              className="text-sm text-primary hover:underline"
            >
              ¿Olvidaste tu contraseña?
            </Link>
          </div>

          <Button type="submit" className="w-full" size="lg" isLoading={isSubmitting}>
            Entrar
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-muted-foreground">
          ¿No tienes cuenta?{" "}
          <Link href="/registro" className="font-medium text-primary hover:underline">
            Crear una cuenta
          </Link>
        </p>
      </CardContent>
    </Card>
  );
}
