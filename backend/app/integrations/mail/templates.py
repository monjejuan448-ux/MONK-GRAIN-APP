"""Plantillas de los correos transaccionales.

Se construyen en Python y no con un motor de plantillas porque son pocas y
sencillas; cuando el catálogo de correos crezca, migran a archivos Jinja.
Todo el texto va en español, conforme a la convención del proyecto.
"""

from dataclasses import dataclass

BRAND_COLOR = "#6F4E37"
ACCENT_COLOR = "#C79A55"
TEXT_COLOR = "#3B2417"
BACKGROUND = "#FFFDF8"


@dataclass(frozen=True)
class MailContent:
    subject: str
    html_body: str
    text_body: str


def _layout(title: str, body_html: str, cta_label: str | None, cta_url: str | None) -> str:
    """Envoltura común de los correos, con estilos en línea.

    Los clientes de correo ignoran las hojas de estilo externas, de modo que el
    estilo debe ir incrustado en cada elemento.
    """
    button = ""
    if cta_label and cta_url:
        button = f"""
        <tr>
          <td style="padding: 8px 0 24px;">
            <a href="{cta_url}"
               style="display:inline-block;background:{BRAND_COLOR};color:#F4EBDD;
                      text-decoration:none;padding:12px 24px;border-radius:8px;
                      font-weight:600;font-size:15px;">{cta_label}</a>
          </td>
        </tr>"""

    fallback = ""
    if cta_url:
        fallback = f"""
        <tr>
          <td style="padding-bottom:24px;font-size:13px;color:#6b625a;">
            Si el botón no funciona, copia este enlace en tu navegador:<br>
            <span style="word-break:break-all;color:{BRAND_COLOR};">{cta_url}</span>
          </td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width"></head>
<body style="margin:0;padding:0;background:{BACKGROUND};
             font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
         style="background:{BACKGROUND};padding:32px 16px;">
    <tr><td align="center">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
             style="max-width:560px;background:#ffffff;border-radius:12px;
                    border:1px solid #e8ded0;padding:32px;">
        <tr>
          <td style="padding-bottom:24px;border-bottom:1px solid #e8ded0;">
            <span style="font-size:20px;font-weight:700;color:{TEXT_COLOR};
                         letter-spacing:-0.02em;">MONK GRAIN</span>
            <span style="display:block;font-size:11px;letter-spacing:0.18em;
                         text-transform:uppercase;color:{ACCENT_COLOR};margin-top:2px;">
              Café de origen
            </span>
          </td>
        </tr>
        <tr>
          <td style="padding:28px 0 12px;">
            <h1 style="margin:0;font-size:22px;color:{TEXT_COLOR};">{title}</h1>
          </td>
        </tr>
        <tr>
          <td style="padding-bottom:24px;font-size:15px;line-height:1.6;color:#4a4038;">
            {body_html}
          </td>
        </tr>
        {button}
        {fallback}
        <tr>
          <td style="padding-top:20px;border-top:1px solid #e8ded0;
                     font-size:12px;color:#8b8078;">
            Este es un mensaje automático de MONK GRAIN. Si no esperabas este
            correo, puedes ignorarlo.
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def verification_email(full_name: str, verification_url: str, expires_hours: int) -> MailContent:
    first_name = full_name.split()[0] if full_name else ""
    return MailContent(
        subject="Confirma tu correo en MONK GRAIN",
        html_body=_layout(
            title=f"Hola{', ' + first_name if first_name else ''}",
            body_html=(
                "<p style='margin:0 0 12px;'>Gracias por unirte a MONK GRAIN. "
                "Confirma tu correo para activar tu cuenta y empezar a comprar "
                "café directamente a los caficultores colombianos.</p>"
                f"<p style='margin:0;'>El enlace vence en {expires_hours} horas.</p>"
            ),
            cta_label="Confirmar mi correo",
            cta_url=verification_url,
        ),
        text_body=(
            f"Hola{' ' + first_name if first_name else ''},\n\n"
            "Gracias por unirte a MONK GRAIN. Confirma tu correo para activar tu cuenta:\n\n"
            f"{verification_url}\n\n"
            f"El enlace vence en {expires_hours} horas.\n\n"
            "Si no creaste esta cuenta, puedes ignorar este mensaje."
        ),
    )


def password_reset_email(full_name: str, reset_url: str, expires_hours: int) -> MailContent:
    first_name = full_name.split()[0] if full_name else ""
    return MailContent(
        subject="Restablece tu contraseña de MONK GRAIN",
        html_body=_layout(
            title=f"Hola{', ' + first_name if first_name else ''}",
            body_html=(
                "<p style='margin:0 0 12px;'>Recibimos una solicitud para "
                "restablecer la contraseña de tu cuenta.</p>"
                f"<p style='margin:0;'>El enlace vence en {expires_hours} hora(s) y "
                "solo puede usarse una vez. Al cambiar tu contraseña, se cerrarán "
                "todas tus sesiones activas.</p>"
            ),
            cta_label="Restablecer contraseña",
            cta_url=reset_url,
        ),
        text_body=(
            f"Hola{' ' + first_name if first_name else ''},\n\n"
            "Recibimos una solicitud para restablecer tu contraseña:\n\n"
            f"{reset_url}\n\n"
            f"El enlace vence en {expires_hours} hora(s) y solo puede usarse una vez.\n\n"
            "Si no solicitaste este cambio, ignora este mensaje: tu contraseña "
            "seguirá siendo la misma."
        ),
    )


def password_changed_email(full_name: str) -> MailContent:
    """Aviso tras un cambio de contraseña.

    Es la señal que permite a la persona detectar un acceso no autorizado, por
    eso se envía siempre y no puede desactivarse.
    """
    first_name = full_name.split()[0] if full_name else ""
    return MailContent(
        subject="Tu contraseña de MONK GRAIN fue cambiada",
        html_body=_layout(
            title="Tu contraseña fue actualizada",
            body_html=(
                f"<p style='margin:0 0 12px;'>Hola{' ' + first_name if first_name else ''}, "
                "la contraseña de tu cuenta se cambió correctamente y se cerraron "
                "todas tus sesiones activas.</p>"
                "<p style='margin:0;'><strong>Si no fuiste tú</strong>, restablece "
                "tu contraseña de inmediato y contacta con soporte.</p>"
            ),
            cta_label=None,
            cta_url=None,
        ),
        text_body=(
            f"Hola{' ' + first_name if first_name else ''},\n\n"
            "La contraseña de tu cuenta MONK GRAIN se cambió correctamente y se "
            "cerraron todas tus sesiones activas.\n\n"
            "Si no fuiste tú, restablece tu contraseña de inmediato y contacta con soporte."
        ),
    )
