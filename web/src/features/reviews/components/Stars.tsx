import { Star } from "lucide-react";

import { cn } from "@/lib/utils";

/**
 * Calificación en estrellas.
 *
 * Las estrellas son decorativas —`aria-hidden`— y el valor se anuncia en texto:
 * un lector de pantalla que enumerase cinco iconos no diría nada útil, y quien
 * no distingue el relleno del contorno necesita el número.
 */
export function Stars({
  rating,
  size = "sm",
  showValue = false,
  count,
}: {
  rating: number;
  size?: "sm" | "md" | "lg";
  showValue?: boolean;
  count?: number;
}) {
  const dimension = { sm: "size-4", md: "size-5", lg: "size-6" }[size];
  const rounded = Math.round(rating);

  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="inline-flex" aria-hidden="true">
        {[1, 2, 3, 4, 5].map((position) => (
          <Star
            key={position}
            className={cn(
              dimension,
              position <= rounded
                ? "fill-gold text-gold"
                : "fill-transparent text-muted-foreground/40",
            )}
          />
        ))}
      </span>
      <span className={showValue ? "text-sm font-medium" : "sr-only"}>
        {rating.toFixed(1).replace(".", ",")} de 5
        {count !== undefined && (
          <span className="font-normal text-muted-foreground">
            {" "}
            · {count} {count === 1 ? "reseña" : "reseñas"}
          </span>
        )}
      </span>
    </span>
  );
}

/** Selector de calificación: cinco botones de radio con apariencia de estrellas. */
export function StarPicker({
  value,
  onChange,
  disabled,
}: {
  value: number;
  onChange: (rating: number) => void;
  disabled?: boolean;
}) {
  return (
    <fieldset className="flex items-center gap-1" disabled={disabled}>
      <legend className="sr-only">Calificación de 1 a 5 estrellas</legend>
      {[1, 2, 3, 4, 5].map((position) => (
        <label
          key={position}
          className="cursor-pointer rounded p-0.5 focus-within:ring-2 focus-within:ring-primary"
        >
          <input
            type="radio"
            name="rating"
            value={position}
            checked={value === position}
            onChange={() => onChange(position)}
            className="sr-only"
          />
          <Star
            className={cn(
              "size-7 transition-colors",
              position <= value
                ? "fill-gold text-gold"
                : "fill-transparent text-muted-foreground/40 hover:text-gold",
            )}
            aria-hidden="true"
          />
          <span className="sr-only">
            {position} {position === 1 ? "estrella" : "estrellas"}
          </span>
        </label>
      ))}
    </fieldset>
  );
}
