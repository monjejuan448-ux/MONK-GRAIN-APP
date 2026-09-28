"use client";

import Link from "next/link";
import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { MailCheck } from "lucide-react";

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
  passwordResetRequestSchema,
  type PasswordResetRequestInput,
} from "@/features/auth/schemas";

export default function RequestPasswordResetPage() {
  const [sent, setSent] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    getValues,
    formState: { errors, isSubmitting },
  } = useForm<PasswordResetRequestInput>({
    resolver: zodResolver(passwordResetRequestSchema),
  });

  async function onSubmit(data: PasswordResetRequestInput) {
    setFormError(null);
    try {
      await authApi.requestPasswordReset(data.email);
      setSent(true);
    } catch {
      // El backend responde igual exista o no la cuenta, así que un error aquí
      // solo puede ser de conexión o de límite de intentos.
      setFormError("No pudimos enviar el correo. Inténtalo de nuevo en unos minutos.");
    }
  }

  if (sent) {
    return (
      <Card>
        <CardContent className="pt-8 text-center">
          <MailCheck className="mx-auto mb-4 size-12 text-forest" aria-hidden="true" />

          <h1 className="font-display text-xl font-semibold">Revisa tu correo</h1>

          {/*
            El mensaje no confirma ni desmiente que la cuenta exista: decirlo
            permitiría averiguar qué correos están registrados en la plataforma.
          */}
          <p className="mt-3 text-sm leading-relaxed text-muted-foreground" role="status">
            Si <strong>{getValues("email")}</strong> corresponde a una cuenta registrada,
            le enviamos un enlace para crear una contraseña nueva. El enlace vence en una
            hora y solo puede usarse una vez.
          </p>

          <p className="mt-4 text-sm text-muted-foreground">
            ¿No te llegó? Revisa la carpeta de correo no deseado antes de volver a
            intentarlo.
          </p>

          <Link
            href="/ingresar"
            className="mt-6 inline-block text-sm font-medium text-primary hover:underline"
          >
            Volver a iniciar sesión
          </Link>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>¿Olvidaste tu contraseña?</CardTitle>
        <CardDescription>
          Escribe el correo con el que te registraste y te enviaremos un enlace para crear
          una nueva.
        </CardDescription>
      </CardHeader>

      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          {formError && (
            <p
              role="alert"
              className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive"
            >
              {formError}
            </p>
          )}

          <div>
            <Label htmlFor="email">Correo electrónico</Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              placeholder="tu@correo.com"
              error={errors.email?.message}
              {...register("email")}
            />
          </div>

          <Button
            type="submit"
            className="w-full"
            disabled={isSubmitting}
            aria-busy={isSubmitting}
          >
            {isSubmitting ? "Enviando…" : "Enviar enlace"}
          </Button>

          <p className="text-center text-sm text-muted-foreground">
            ¿Ya la recordaste?{" "}
            <Link href="/ingresar" className="font-medium text-primary hover:underline">
              Iniciar sesión
            </Link>
          </p>
        </form>
      </CardContent>
    </Card>
  );
}
