import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva("inline-flex items-center rounded-full font-medium", {
  variants: {
    variant: {
      default: "bg-muted text-muted-foreground",
      primary: "bg-primary/10 text-primary",
      secondary: "bg-secondary/10 text-secondary",
      accent: "bg-accent/15 text-accent-foreground",
      outline: "border border-border text-foreground",
      success: "bg-forest/10 text-forest",
      warning: "bg-gold/20 text-coffee-dark",
      /**
       * Para fondos oscuros. Las variantes translúcidas de arriba heredan un
       * texto pensado para fondo claro: sobre la portada oscura quedaban en
       * 1.02:1 de contraste, es decir, ilegibles. Este dorado sólido con texto
       * café oscuro alcanza 5.5:1 y cumple WCAG AA.
       */
      spotlight: "bg-gold text-coffee-dark",
    },
    size: {
      sm: "px-2.5 py-0.5 text-xs",
      md: "px-3.5 py-1 text-sm",
    },
  },
  defaultVariants: { variant: "default", size: "sm" },
});

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, size, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant, size }), className)} {...props} />;
}
