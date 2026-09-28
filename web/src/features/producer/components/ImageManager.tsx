"use client";

import { useRef, useState } from "react";
import { ImagePlus, Star, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { CoffeeImage } from "@/components/shared/CoffeeImage";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { producerCatalogApi, type ProducerProduct } from "@/features/producer/api";
import { ApiError } from "@/lib/api";

const MAX_MB = 5;

interface ImageManagerProps {
  token: string;
  product: ProducerProduct;
  onChange: (product: ProducerProduct) => void;
}

export function ImageManager({ token, product, onChange }: ImageManagerProps) {
  const [isUploading, setIsUploading] = useState(false);
  const [altText, setAltText] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);

  async function handleFile(file: File) {
    // Se avisa aquí del tamaño para no hacer subir 20 MB por la red antes de
    // que el servidor los rechace. El límite real lo impone el backend.
    if (file.size > MAX_MB * 1024 * 1024) {
      toast.error(`La imagen supera los ${MAX_MB} MB. Usa una más liviana.`);
      return;
    }

    setIsUploading(true);
    try {
      onChange(await producerCatalogApi.uploadImage(token, product.id, file, altText));
      setAltText("");
      if (fileInput.current) fileInput.current.value = "";
      toast.success("Fotografía agregada.");
    } catch (error) {
      toast.error(
        error instanceof ApiError ? error.message : "No pudimos subir la imagen.",
      );
    } finally {
      setIsUploading(false);
    }
  }

  async function remove(imageId: string) {
    try {
      onChange(await producerCatalogApi.deleteImage(token, product.id, imageId));
      toast.success("Fotografía eliminada.");
    } catch {
      toast.error("No pudimos eliminar la fotografía.");
    }
  }

  return (
    <section aria-labelledby="fotos-titulo" className="space-y-4">
      <div>
        <h2 id="fotos-titulo" className="font-display text-lg font-semibold">
          Fotografías
        </h2>
        <p className="text-sm text-muted-foreground">
          La primera es la portada del café. Se admiten JPEG, PNG y WebP hasta {MAX_MB}{" "}
          MB.
        </p>
      </div>

      {product.images.length > 0 && (
        <ul className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {product.images.map((image) => (
            <li key={image.id} className="relative">
              <div className="relative aspect-square overflow-hidden rounded-md border border-border bg-muted">
                <CoffeeImage
                  src={image.image_url}
                  alt={image.alt_text ?? product.name}
                  sizes="(max-width: 640px) 50vw, 200px"
                  className="object-cover"
                />
              </div>

              {image.is_primary && (
                <Badge variant="accent" className="absolute left-2 top-2">
                  <Star className="mr-1 size-3" aria-hidden="true" />
                  Portada
                </Badge>
              )}

              <Button
                type="button"
                variant="outline"
                size="sm"
                className="mt-2 w-full"
                onClick={() => remove(image.id)}
              >
                <Trash2 className="mr-1.5 size-4" aria-hidden="true" />
                Eliminar
              </Button>
            </li>
          ))}
        </ul>
      )}

      <div className="rounded-md border border-dashed border-border p-4">
        <div className="space-y-3">
          <div>
            <label htmlFor="alt_text" className="mb-1.5 block text-sm font-medium">
              Descripción de la imagen
            </label>
            <Input
              id="alt_text"
              value={altText}
              onChange={(event) => setAltText(event.target.value)}
              placeholder="Ej.: pergamino seco en la marquesina"
              maxLength={200}
            />
            <p className="mt-1.5 text-xs text-muted-foreground">
              La leen quienes navegan con lector de pantalla. Si la dejas vacía usamos el
              nombre del café.
            </p>
          </div>

          <input
            ref={fileInput}
            id="foto"
            type="file"
            accept="image/jpeg,image/png,image/webp"
            className="sr-only"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) void handleFile(file);
            }}
          />
          <Button
            type="button"
            variant="outline"
            disabled={isUploading}
            aria-busy={isUploading}
            onClick={() => fileInput.current?.click()}
          >
            <ImagePlus className="mr-1.5 size-4" aria-hidden="true" />
            {isUploading ? "Subiendo…" : "Agregar fotografía"}
          </Button>
        </div>
      </div>
    </section>
  );
}
