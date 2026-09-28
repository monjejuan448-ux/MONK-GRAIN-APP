import type { LucideIcon } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: string | number;
  hint?: string;
  icon?: LucideIcon;
  /** Resalta la tarjeta cuando el dato requiere atención (stock bajo, pendientes). */
  emphasis?: "default" | "warning" | "success";
}

export function StatCard({
  label,
  value,
  hint,
  icon: Icon,
  emphasis = "default",
}: StatCardProps) {
  return (
    <Card
      className={cn(
        emphasis === "warning" && "border-gold/50 bg-gold/5",
        emphasis === "success" && "border-forest/30 bg-forest/5",
      )}
    >
      <CardContent className="pt-6">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-sm text-muted-foreground">{label}</p>
            <p className="mt-1 font-display text-2xl font-bold tabular-nums">{value}</p>
            {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
          </div>
          {Icon && (
            <Icon
              className={cn(
                "size-5 shrink-0",
                emphasis === "warning" ? "text-gold" : "text-muted-foreground",
              )}
              aria-hidden="true"
            />
          )}
        </div>
      </CardContent>
    </Card>
  );
}
