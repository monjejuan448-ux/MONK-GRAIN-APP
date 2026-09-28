import { z } from "zod";

/**
 * Validación de los formularios de acceso.
 *
 * Las reglas replican las del backend para dar retroalimentación inmediata,
 * pero no lo sustituyen: la validación del servidor sigue siendo la que manda.
 */

const email = z
  .string()
  .min(1, "Escribe tu correo electrónico")
  .email("El correo no tiene un formato válido");

const password = z
  .string()
  .min(12, "La contraseña debe tener al menos 12 caracteres")
  .regex(/[a-zA-Z]/, "Debe incluir al menos una letra")
  .regex(/\d/, "Debe incluir al menos un número");

export const loginSchema = z.object({
  email,
  password: z.string().min(1, "Escribe tu contraseña"),
});

export const registerSchema = z
  .object({
    fullName: z
      .string()
      .min(3, "Escribe tu nombre completo")
      .max(150, "El nombre es demasiado largo"),
    email,
    phone: z
      .string()
      .regex(/^3\d{9}$/, "Escribe un celular colombiano de 10 dígitos")
      .or(z.literal(""))
      .optional(),
    password,
    confirmPassword: z.string(),
    dataConsent: z.literal(true, {
      errorMap: () => ({
        message: "Debes autorizar el tratamiento de tus datos para crear la cuenta",
      }),
    }),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Las contraseñas no coinciden",
    path: ["confirmPassword"],
  });

export const passwordResetRequestSchema = z.object({ email });

export const passwordResetConfirmSchema = z
  .object({
    password,
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Las contraseñas no coinciden",
    path: ["confirmPassword"],
  });

export type LoginInput = z.infer<typeof loginSchema>;
export type RegisterInput = z.infer<typeof registerSchema>;
export type PasswordResetRequestInput = z.infer<typeof passwordResetRequestSchema>;
export type PasswordResetConfirmInput = z.infer<typeof passwordResetConfirmSchema>;
