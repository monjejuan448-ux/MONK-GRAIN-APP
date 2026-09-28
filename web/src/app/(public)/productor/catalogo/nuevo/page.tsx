"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ArrowLeft } from "lucide-react";
import { toast } from "sonner";

import { ProductForm } from "@/features/producer/components/ProductForm";
import { producerCatalogApi, type ProductInput } from "@/features/producer/api";
import { ApiError } from "@/lib/api";
import { session } from "@/lib/session";

export default function NewProductPage() {
  const router = useRouter();
  const [isSaving, setIsSaving] = useState(false);

  async function create(input: ProductInput) {
    const token = session.getAccessToken();
    if (!token) {
      router.push("/ingresar");
      return;
    }

    setIsSaving(true);
    try {
      const product = await producerCatalogApi.create(token, input);
      toast.success("Café creado. Ahora agrega fotos y presentaciones para publicarlo.");
      // Se continúa en la edición: allí se suben las fotos y se define el
      // inventario, que es lo que falta para poder publicar.
      router.push(`/productor/catalogo/${product.id}`);
    } catch (error) {
      toast.error(
        error instanceof ApiError ? error.message : "No pudimos crear el café.",
      );
      setIsSaving(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <Link
        href="/productor/catalogo"
        className="mb-6 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
        Volver a mi catálogo
      </Link>

      <h1 className="font-display text-3xl font-bold">Publicar un lote</h1>
      <p className="mb-8 mt-1 text-muted-foreground">
        Empieza por lo esencial. Se guardará como borrador hasta que agregues fotografía y
        presentación.
      </p>

      <ProductForm onSubmit={create} isSaving={isSaving} />
    </div>
  );
}
