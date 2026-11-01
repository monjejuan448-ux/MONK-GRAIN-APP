import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Política de privacidad",
  description:
    "Cómo MONK GRAIN maneja tu información, qué guarda en tu navegador y qué información " +
    "de los productores permanece reservada.",
};

export default function PrivacyPage() {
  return (
    <>
      <h1>Política de privacidad</h1>
      <p className="text-sm text-muted-foreground">
        Vigente desde [fecha] · Última actualización: [fecha]
      </p>

      <p>
        Este documento explica en términos claros cómo manejamos tu información. El
        detalle legal de la recolección, los plazos y tus derechos está en la{" "}
        <Link href="/legal/datos">política de tratamiento de datos</Link>, redactada
        conforme a la Ley 1581 de 2012. Si algo de esta página parece contradecir aquella,{" "}
        <strong>prevalece la política de tratamiento de datos</strong>.
      </p>

      <h2>1. Nuestro criterio</h2>
      <p>
        Pedimos lo mínimo necesario para que puedas comprar o vender café, y no lo usamos
        para nada más. No vendemos datos personales ni los cedemos con fines publicitarios
        de terceros. Tampoco recogemos datos sensibles: nada sobre tu salud, tus
        creencias, tu origen étnico o tu vida privada.
      </p>

      <h2>2. Qué guardamos en tu navegador</h2>
      <p>
        MONK GRAIN{" "}
        <strong>no usa cookies de publicidad ni de seguimiento de terceros</strong>. Lo
        que almacenamos es lo indispensable para que la plataforma funcione:
      </p>
      <ul>
        <li>
          <strong>Tu sesión:</strong> mientras estás dentro, el navegador guarda la
          credencial que te identifica. Se borra al cerrar sesión o al cerrar la pestaña.
        </li>
        <li>
          <strong>Tu carrito, si aún no has iniciado sesión:</strong> queda guardado en tu
          navegador para que no lo pierdas, y se fusiona con el de tu cuenta cuando
          ingresas. A diferencia de la sesión, este sí sobrevive al cierre de la pestaña;
          se borra al vaciar el carrito o al limpiar los datos del navegador.
        </li>
        <li>
          <strong>Tus preferencias:</strong> por ejemplo el idioma seleccionado.
        </li>
      </ul>
      <p>
        No hay analítica de terceros ni píxeles de redes sociales. Si eso cambiara, lo
        anunciaríamos y pediríamos tu consentimiento antes de activarlo.
      </p>

      <h2>3. Qué información de los productores es reservada</h2>
      <p>
        Un caficultor publica su café sin exponer su vida privada.{" "}
        <strong>Nunca se publican en el catálogo:</strong>
      </p>
      <ul>
        <li>
          <strong>La ubicación exacta de la finca.</strong> El catálogo muestra el
          municipio y una posición aproximada, nunca las coordenadas precisas.
        </li>
        <li>El número de documento o NIT.</li>
        <li>
          La dirección física de notificaciones, el correo y el teléfono de contacto.
        </li>
        <li>
          Los documentos de certificación, que solo abren su titular y el equipo de MONK
          GRAIN mediante un enlace temporal.
        </li>
      </ul>
      <p>
        Además, cuando subes una fotografía <strong>eliminamos sus metadatos</strong>:
        muchas cámaras y teléfonos guardan en la imagen las coordenadas donde se tomó, y
        esa información no debe viajar con la foto de tu finca.
      </p>

      <h3>La excepción que impone la ley</h3>
      <p>
        Hay un caso en que sí entregamos los datos de identificación de un vendedor:
        cuando alguien que le compró necesita presentarle una queja o un reclamo. El{" "}
        <strong>artículo 53 de la Ley 1480 de 2011</strong> obliga a las plataformas como
        la nuestra a llevar un registro con el nombre o razón social, el documento de
        identificación, la dirección física de notificaciones y el teléfono de cada
        oferente, y a ponerlo a disposición de quien compró y de la autoridad competente
        cuando lo pida.
      </p>
      <p>
        Eso no significa publicarlos. Significa que quien tiene un reclamo concreto puede
        saber a quién dirigirlo, que es exactamente lo que necesita para hacer valer su
        garantía.
      </p>

      <h2>4. Qué ve cada quien</h2>
      <ul>
        <li>
          <strong>Cualquier visitante:</strong> el catálogo, las fichas de café y el
          perfil público de los productores.
        </li>
        <li>
          <strong>Quien te vende:</strong> tu nombre, teléfono y dirección, solo de los
          pedidos que te despacha. Desde ese momento el vendedor responde por esos datos
          por su cuenta y solo puede usarlos para despacharte y atender tu garantía.
        </li>
        <li>
          <strong>Quien compra:</strong> únicamente sus propios pedidos.
        </li>
        <li>
          <strong>El equipo de MONK GRAIN:</strong> lo necesario para operar la plataforma
          y atender reclamos. Las acciones administrativas sensibles quedan registradas
          con su autor y su fecha.
        </li>
      </ul>

      <h2>5. Seguridad</h2>
      <ul>
        <li>
          Las contraseñas se guardan transformadas con un algoritmo de un solo sentido: no
          pueden recuperarse, solo restablecerse.
        </li>
        <li>
          Al cambiar tu contraseña se cierran todas las sesiones abiertas en otros
          dispositivos.
        </li>
        <li>
          Limitamos los intentos de inicio de sesión para dificultar los ataques por
          fuerza bruta.
        </li>
        <li>Los archivos que se suben se validan por su contenido, no por su nombre.</li>
      </ul>
      <p>
        Ninguna medida elimina el riesgo por completo. Si ocurriera un incidente que
        afecte tus datos te avisaremos y lo reportaremos a la Superintendencia de
        Industria y Comercio en el plazo que fija la ley.
      </p>

      <h2>6. Correos y mensajes que enviamos</h2>
      <p>
        Los correos sobre tus pedidos, tu cuenta y tu seguridad forman parte del servicio
        y no pueden desactivarse mientras tengas una cuenta activa.
      </p>
      <p>
        <strong>Los mensajes comerciales o publicitarios son otra cosa:</strong> solo te
        los enviamos por los canales que hayas autorizado expresamente, y puedes revocar
        esa autorización cuando quieras desde tu cuenta o escribiendo a [correo]. Es lo
        que exige la Ley 2300 de 2023, que además limita los horarios y la frecuencia con
        que se puede contactar a un consumidor.
      </p>

      <h2>7. Tus derechos</h2>
      <p>
        Puedes consultar, corregir, actualizar o suprimir tus datos, pedir prueba de la
        autorización que otorgaste y revocarla. El procedimiento y los plazos están en la{" "}
        <Link href="/legal/datos">política de tratamiento de datos</Link>.
      </p>
      <p>
        Si no quedas conforme con nuestra respuesta puedes acudir a la{" "}
        <strong>Superintendencia de Industria y Comercio</strong>:{" "}
        <a href="https://www.sic.gov.co" target="_blank" rel="noopener noreferrer">
          www.sic.gov.co
        </a>
        . Ten en cuenta que la ley exige haber presentado antes la consulta o el reclamo
        ante nosotros.
      </p>

      <h2>8. Contacto</h2>
      <p>
        Para cualquier asunto sobre tu privacidad, escribe a <strong>[correo]</strong>.
      </p>

      <hr />
      <p className="text-sm text-muted-foreground">
        Ver también los <Link href="/legal/terminos">términos y condiciones</Link> y la{" "}
        <Link href="/legal/devoluciones">política de devoluciones</Link>.
      </p>
    </>
  );
}
