"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { CheckCircle2, XCircle } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/shared/states";
import { authApi } from "@/features/auth/api";
import { ApiError } from "@/lib/api";

type VerificationState = "verifying" | "success" | "error";

function VerifyEmailContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [state, setState] = useState<VerificationState>("verifying");
  const [message, setMessage] = useState("");
  // React 18+ monta dos veces en desarrollo; sin esta guarda, el token de un
  // solo uso se consumiría en la primera llamada y la segunda mostraría error.
  const hasRun = useRef(false);

  useEffect(() => {
    if (hasRun.current) return;
    hasRun.current = true;

    if (!token) {
      setState("error");
      setMessage("El enlace no incluye un token de verificación.");
      return;
    }

    authApi
      .verifyEmail(token)
      .then((response) => {
        setState("success");
        setMessage(response.message);
      })
      .catch((error) => {
        setState("error");
        setMessage(
          error instanceof ApiError
            ? error.message
            : "No pudimos conectar con el servidor. Inténtalo de nuevo.",
        );
      });
  }, [token]);

  if (state === "verifying") {
    return (
      <CardContent className="pt-8 text-center" aria-busy="true">
        <Skeleton className="mx-auto mb-4 size-12 rounded-full" />
        <Skeleton className="mx-auto mb-2 h-6 w-48" />
        <Skeleton className="mx-auto h-4 w-64" />
        <p className="sr-only">Verificando tu correo electrónico…</p>
      </CardContent>
    );
  }

  return (
    <CardContent className="pt-8 text-center">
      {state === "success" ? (
        <CheckCircle2 className="mx-auto mb-4 size-12 text-forest" aria-hidden="true" />
      ) : (
        <XCircle className="mx-auto mb-4 size-12 text-destructive" aria-hidden="true" />
      )}

      <h1 className="font-display text-xl font-semibold">
        {state === "success" ? "Correo verificado" : "No pudimos verificar tu correo"}
      </h1>

      <p className="mt-3 text-sm leading-relaxed text-muted-foreground" role="status">
        {message}
      </p>

      <Link
        href="/ingresar"
        className="mt-6 inline-block text-sm font-medium text-primary hover:underline"
      >
        {state === "success" ? "Iniciar sesión" : "Volver a iniciar sesión"}
      </Link>
    </CardContent>
  );
}

export default function VerifyEmailPage() {
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
        <VerifyEmailContent />
      </Suspense>
    </Card>
  );
}
