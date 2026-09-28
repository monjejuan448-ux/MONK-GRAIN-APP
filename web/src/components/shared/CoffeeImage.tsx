"use client";

import Image from "next/image";
import { useEffect, useRef, useState } from "react";

import { cn } from "@/lib/utils";

interface CoffeeImageProps {
  /** URL de la imagen. Si falta, se muestra el marcador directamente. */
  src?: string | null;
  /** Texto alternativo. Se conserva en el marcador para los lectores de pantalla. */
  alt: string;
  sizes?: string;
  className?: string;
  priority?: boolean;
}

/**
 * Imagen de café con marcador de posición.
 *
 * Una URL válida no garantiza que el archivo exista: el objeto puede haberse
 * borrado del almacenamiento o no haberse subido nunca. Sin este componente el
 * navegador dibuja el icono de imagen rota, que en una ficha de producto parece
 * un error de la tienda.
 *
 * El marcador no es un hueco gris: usa los colores de la marca para que la
 * ficha se lea como una tarjeta sin fotografía, no como una tarjeta estropeada.
 */
export function CoffeeImage({ src, alt, sizes, className, priority }: CoffeeImageProps) {
  const [failed, setFailed] = useState(false);
  const imageRef = useRef<HTMLImageElement>(null);

  // No basta con el `onError` de React. El evento `error` de una imagen no
  // burbujea, y con renderizado en servidor la carga puede fallar antes de que
  // la página se hidrate: en ese caso el manejador nunca llega a existir y la
  // ficha se queda con el icono de imagen rota.
  //
  // Por eso aquí se hacen dos cosas al montar: comprobar si el elemento ya está
  // fallido —una imagen terminada con ancho cero es una imagen rota— y escuchar
  // el evento directamente sobre el nodo, sin depender del sistema de eventos
  // sintéticos.
  useEffect(() => {
    const element = imageRef.current;
    if (!element) return;

    if (element.complete && element.naturalWidth === 0) {
      setFailed(true);
      return;
    }

    const handleError = () => setFailed(true);
    element.addEventListener("error", handleError);
    return () => element.removeEventListener("error", handleError);
  }, [src]);

  if (!src || failed) {
    return <CoffeeImagePlaceholder alt={alt} />;
  }

  return (
    <Image
      ref={imageRef}
      src={src}
      alt={alt}
      fill
      sizes={sizes}
      priority={priority}
      className={className}
      onError={() => setFailed(true)}
    />
  );
}

/**
 * Marcador con un grano de café sobre un fondo cálido.
 *
 * Lleva `role="img"` y `aria-label`: quien navega con lector de pantalla sigue
 * sabiendo de qué café se trata aunque no haya fotografía. El dibujo queda
 * oculto para la accesibilidad porque el nombre ya lo aporta la etiqueta.
 */
function CoffeeImagePlaceholder({ alt }: { alt: string }) {
  return (
    <div
      role="img"
      aria-label={`${alt} (sin fotografía disponible)`}
      className={cn(
        "flex h-full w-full flex-col items-center justify-center gap-2",
        "bg-gradient-to-br from-cream to-[#E4D5BE]",
      )}
    >
      <svg
        viewBox="0 0 48 48"
        className="size-10 text-coffee/35"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.5"
        aria-hidden="true"
      >
        {/* Grano de café: elipse inclinada con el surco central. */}
        <ellipse cx="24" cy="24" rx="12" ry="17" transform="rotate(-30 24 24)" />
        <path d="M17 32c3-5 3-11 0-16" strokeLinecap="round" />
      </svg>
      <span className="px-2 text-center text-[11px] font-medium uppercase tracking-wider text-coffee/45">
        Sin fotografía
      </span>
    </div>
  );
}
