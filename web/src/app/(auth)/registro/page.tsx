"use client";

import Link from "next/link";
import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { CheckCircle2 } from "lucide-react";
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
import { registerSchema, type RegisterInput } from "@/features/auth/schemas";
import { ApiError } from "@/lib/api";

export default function RegisterPage() {
  const [submitted, setSubmitted] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<RegisterInput>({ resolver: zodResolver(registerSchema) });

  async function onSubmit(data: RegisterInput) {
    setFormError(null);
    try {
      await authApi.register({
        email: data.email,
        password: data.password,
        full_name: data.fullName,
        phone: data.phone || null,
        data_consent: data.dataConsent,
      });
      setSubmitted(true);
    } catch (error) {
      if (error instanceof ApiError) {
        // El backend devuelve los errores por campo; se muestran junto al que
        // corresponde en vez de en un mensaje global sin contexto.
        const fieldMap: Record<string, keyof RegisterInput> = {
          email: "email",
          password: "password",
          full_name: "fullName",
          phone: "phone",
          data_consent: "dataConsent",
        };
        let handled = false;
        for (const [apiField, message] of Object.entries(error.fieldErrors)) {
          const formField = fieldMap[apiField];
          if (formField) {
            setError(formField, { message });
            handled = true;
          }
        }
        if (!handled) setFormError(error.message);
      } else {
        setFormError("No pudimos conectar con el servidor. Inténtalo de nuevo.");
      }
    }
  }

  if (submitted) {
    return (
      <Card>
        <CardContent className="pt-8 text-center">
          <CheckCircle2 className="mx-auto mb-4 size-12 text-forest" aria-hidden="true" />
          <h1 className="font-display text-xl font-semibold">Revisa tu correo</h1>
          <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
            Si el correo no estaba registrado, te enviamos un enlace para confirmar tu
            cuenta. El enlace vence en 24 horas.
          </p>
          <Link
            href="/ingresar"
            className="mt-6 inline-block text-sm font-medium text-primary hover:underline"
          >
            Ir a iniciar sesión
          </Link>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-2xl">Crear cuenta</CardTitle>
        <CardDescription>
          Compra café directamente a los caficultores colombianos.
        </CardDescription>
      </CardHeader>

      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} noValidate>
          {formError && (
            <div
              className="mb-5 rounded-md border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive"
              role="alert"
            >
              {formError}
            </div>
          )}

          <div className="mb-4">
            <Label htmlFor="fullName" required>
              Nombre completo
            </Label>
            <Input
              id="fullName"
              autoComplete="name"
              placeholder="María López"
              error={errors.fullName?.message}
              {...register("fullName")}
            />
          </div>

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

          <div className="mb-4">
            <Label htmlFor="phone">Celular</Label>
            <Input
              id="phone"
              type="tel"
              autoComplete="tel"
              placeholder="3001234567"
              error={errors.phone?.message}
              {...register("phone")}
            />
            <p className="mt-1 text-xs text-muted-foreground">
              Opcional. Lo usamos para avisarte sobre tus pedidos.
            </p>
          </div>

          <div className="mb-4">
            <Label htmlFor="password" required>
              Contraseña
            </Label>
            <Input
              id="password"
              type="password"
              autoComplete="new-password"
              error={errors.password?.message}
              {...register("password")}
            />
            <p className="mt-1 text-xs text-muted-foreground">
              Mínimo 12 caracteres, con al menos una letra y un número.
            </p>
          </div>

          <div className="mb-5">
            <Label htmlFor="confirmPassword" required>
              Confirmar contraseña
            </Label>
            <Input
              id="confirmPassword"
              type="password"
              autoComplete="new-password"
              error={errors.confirmPassword?.message}
              {...register("confirmPassword")}
            />
          </div>

          {/* El consentimiento debe ser explícito y no puede venir marcado por
              defecto: la Ley 1581 de 2012 no admite consentimiento tácito. */}
          <div className="mb-6">
            <div className="flex items-start gap-3">
              <input
                id="dataConsent"
                type="checkbox"
                className="mt-1 size-4 shrink-0 rounded border-input accent-primary"
                aria-describedby={errors.dataConsent ? "dataConsent-error" : undefined}
                {...register("dataConsent")}
              />
              <label htmlFor="dataConsent" className="text-sm leading-relaxed">
                Autorizo el tratamiento de mis datos personales conforme a la{" "}
                <Link
                  href="/legal/datos"
                  className="text-primary underline"
                  target="_blank"
                >
                  política de tratamiento de datos
                </Link>{" "}
                (Ley 1581 de 2012).
              </label>
            </div>
            {errors.dataConsent && (
              <p
                id="dataConsent-error"
                className="mt-1.5 text-sm text-destructive"
                role="alert"
              >
                {errors.dataConsent.message}
              </p>
            )}
          </div>

          <Button type="submit" className="w-full" size="lg" isLoading={isSubmitting}>
            Crear cuenta
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-muted-foreground">
          ¿Ya tienes cuenta?{" "}
          <Link href="/ingresar" className="font-medium text-primary hover:underline">
            Iniciar sesión
          </Link>
        </p>
      </CardContent>
    </Card>
  );
}
