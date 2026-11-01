import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Política de tratamiento de datos",
  description:
    "Política de tratamiento de datos personales de MONK GRAIN conforme a la Ley 1581 de " +
    "2012 y el Decreto 1074 de 2015.",
};

export default function DataPolicyPage() {
  return (
    <>
      <h1>Política de tratamiento de datos personales</h1>
      <p className="text-sm text-muted-foreground">
        Vigente desde [fecha] · Última actualización: [fecha]
      </p>

      <h2>1. Responsable del tratamiento</h2>
      <p>
        <strong>[Razón social]</strong>, identificada con NIT [número], es la responsable
        del tratamiento de los datos personales recogidos a través de la plataforma MONK
        GRAIN.
      </p>
      <ul>
        <li>
          <strong>Domicilio y dirección:</strong> [dirección], [ciudad], Colombia
        </li>
        <li>
          <strong>Correo para asuntos de datos personales:</strong> [correo]
        </li>
        <li>
          <strong>Teléfono:</strong> [teléfono]
        </li>
        <li>
          <strong>Área responsable de atender tus solicitudes:</strong> [área o cargo
          designado], que es quien tramita las peticiones, consultas y reclamos sobre
          datos personales.
        </li>
      </ul>

      <h2>2. Marco legal</h2>
      <p>
        Esta política se adopta en cumplimiento de la <strong>Ley 1581 de 2012</strong>,
        del <strong>Decreto 1074 de 2015</strong> —que compiló el Decreto 1377 de 2013— y
        de las instrucciones que imparte la Superintendencia de Industria y Comercio en su
        Circular Única.
      </p>

      <h2>3. Qué datos recogemos</h2>
      <p>
        Solo pedimos lo necesario para que la plataforma funcione. Te informamos qué
        recogemos y para qué en el momento en que te pedimos la autorización, y guardamos
        constancia de esa autorización con su fecha y hora.
      </p>

      <h3>De toda persona que crea una cuenta</h3>
      <ul>
        <li>Nombre completo y correo electrónico.</li>
        <li>Teléfono, cuando decides aportarlo.</li>
        <li>
          Contraseña, que no se guarda tal cual: se transforma con un algoritmo de un solo
          sentido, de modo que nadie en MONK GRAIN puede leerla ni recuperarla.
        </li>
        <li>Fotografía de perfil, si decides subir una.</li>
        <li>Idioma de tu preferencia y si aceptas o no recibir correos comerciales.</li>
        <li>Fecha y hora en que autorizaste esta política.</li>
        <li>
          Fecha del último acceso y dirección IP asociada a las operaciones sensibles, en
          un registro de auditoría.
        </li>
      </ul>

      <h3>De quien compra</h3>
      <ul>
        <li>
          Direcciones de envío: destinatario, teléfono, departamento, municipio,
          dirección, barrio e indicaciones de entrega.
        </li>
        <li>Historial de pedidos, solicitudes de devolución y reseñas publicadas.</li>
      </ul>

      <h3>De quien vende</h3>
      <ul>
        <li>Razón social, número de documento o NIT y nombre comercial.</li>
        <li>Dirección física de notificaciones y teléfono de contacto.</li>
        <li>Ubicación de la finca o la sede, y capacidad de producción.</li>
        <li>Historia del productor y fotografías que decida publicar.</li>
        <li>Certificaciones con su número, vigencia y documento de respaldo.</li>
      </ul>
      <p>
        Los tres primeros datos de esta lista no son opcionales: el artículo 53 de la Ley
        1480 de 2011 obliga a las plataformas como la nuestra a llevar un registro con la
        identificación de cada oferente, para que un comprador pueda presentarle una
        queja.
      </p>

      <h3>Datos sensibles</h3>
      <p>
        <strong>MONK GRAIN no recoge datos sensibles</strong> en el sentido del artículo 5
        de la Ley 1581 de 2012: no pedimos datos de salud, origen racial o étnico,
        convicciones religiosas o filosóficas, orientación política, vida sexual ni datos
        biométricos. Si en algún momento llegáramos a pedirlos, te informaríamos que{" "}
        <strong>responder es facultativo</strong> y necesitaríamos tu autorización
        explícita.
      </p>

      <h3>Datos de pago</h3>
      <p>
        <strong>No almacenamos números de tarjeta ni códigos de seguridad.</strong> El
        cobro lo procesa una pasarela de pagos certificada, que nos devuelve únicamente
        una referencia de la transacción y su estado.
      </p>
      <p className="rounded-md border border-border bg-muted/40 p-3 text-sm">
        <strong>Estado actual:</strong> la plataforma opera hoy con un proveedor de pago{" "}
        <strong>simulado</strong>, sin cobro real de dinero y sin que se recoja ningún
        dato de tarjeta. Lo descrito en este apartado regirá cuando se active una pasarela
        con cobro efectivo.
      </p>

      <h2>4. Para qué los usamos</h2>
      <ul>
        <li>Crear y administrar tu cuenta, y verificar tu identidad al ingresar.</li>
        <li>Procesar pedidos, coordinar el envío y liquidar el pago a quien vende.</li>
        <li>
          Enviarte correos sobre el estado de tus pedidos, tu cuenta y tu seguridad.
        </li>
        <li>
          Verificar las solicitudes de vendedores y la vigencia de sus certificaciones.
        </li>
        <li>Atender preguntas, reclamos y solicitudes de devolución.</li>
        <li>Prevenir fraude y proteger la seguridad de la plataforma.</li>
        <li>Cumplir obligaciones legales, contables, tributarias y de facturación.</li>
      </ul>
      <p>
        Los correos comerciales solo se envían si los autorizas, y puedes desactivarlos
        desde tu cuenta en cualquier momento sin perder los avisos de tus pedidos.{" "}
        <strong>
          No usamos tus datos para ninguna finalidad distinta de las anteriores
        </strong>
        ; si en el futuro quisiéramos hacerlo, te pediríamos una nueva autorización.
      </p>

      <h2>5. Qué información es pública</h2>
      <p>
        Al publicar un café, cierta información queda visible para cualquier visitante: el
        nombre comercial, la historia, el municipio y el departamento, las certificaciones
        declaradas y la <strong>ubicación aproximada</strong> de la finca.
      </p>
      <p>
        <strong>La ubicación exacta de la finca no se publica nunca.</strong> Tampoco se
        publican el número de documento, la dirección de notificaciones, el teléfono ni el
        correo de quien vende. Los documentos de
        certificación son privados: solo los abren su titular y el equipo de MONK GRAIN.
      </p>
      <p>
        Hay una excepción que la ley nos impone: cuando alguien que compró un café
        necesite presentar una queja o un reclamo, le entregaremos los datos de
        identificación y notificación del vendedor —nombre o razón social, documento,
        dirección física y teléfono—, y también los entregaremos a la autoridad competente
        si los pide. Esto no equivale a publicarlos: se entregan a quien tiene un reclamo
        concreto y con esa finalidad.
      </p>
      <p>
        Las reseñas se publican con el nombre de quien las escribe. Si prefieres no
        aparecer, puedes no publicar reseñas.
      </p>

      <h2>6. Con quién los compartimos</h2>
      <p>
        Compartimos datos únicamente con quien es indispensable para prestarte el
        servicio:
      </p>
      <ul>
        <li>
          <strong>Quien te vende:</strong> recibe tu nombre, teléfono y dirección de
          envío, solo de los pedidos que te despacha. A partir de ese momento el vendedor
          es <strong>responsable independiente</strong> de esos datos y debe usarlos
          únicamente para despacharte el pedido y atender tu garantía.
        </li>
        <li>
          <strong>El operador logístico:</strong> los datos necesarios para entregarte el
          pedido.
        </li>
        <li>
          <strong>La pasarela de pagos:</strong> los datos que exige la transacción.
        </li>
        <li>
          <strong>Nuestros proveedores de tecnología</strong> (alojamiento, correo,
          almacenamiento de archivos), que actúan como <strong>encargados</strong>: tratan
          los datos siguiendo nuestras instrucciones, bajo contrato escrito que les impone
          confidencialidad y medidas de seguridad, y no pueden usarlos para fines propios.
        </li>
        <li>
          <strong>Autoridades:</strong> cuando una orden judicial o una obligación legal
          lo exija.
        </li>
      </ul>
      <p>No vendemos ni cedemos datos personales con fines publicitarios de terceros.</p>

      <h3>Datos fuera de Colombia</h3>
      <p>
        La plataforma opera solo en Colombia, pero algunos servicios de tecnología pueden
        alojar información en servidores ubicados en [país o países]. El artículo 26 de la
        Ley 1581 de 2012 prohíbe transferir datos a países que no ofrezcan un nivel
        adecuado de protección, salvo que el titular lo autorice expresamente. Al aceptar
        esta política <strong>autorizas expresamente esa transferencia</strong> para las
        finalidades descritas aquí, y nos comprometemos a exigir a esos proveedores
        condiciones de seguridad y confidencialidad equivalentes a las que impone la ley
        colombiana.
      </p>

      <h2>7. Tus derechos</h2>
      <p>La ley te reconoce, sobre tus datos, el derecho a:</p>
      <ul>
        <li>Conocer cuáles tenemos y cómo los usamos, de forma gratuita.</li>
        <li>Actualizarlos o rectificarlos cuando estén incompletos o equivocados.</li>
        <li>Solicitar prueba de la autorización que otorgaste.</li>
        <li>Ser informado, cuando lo pidas, del uso que les hemos dado.</li>
        <li>Revocar la autorización y pedir que se supriman.</li>
        <li>
          Presentar quejas ante la{" "}
          <strong>Superintendencia de Industria y Comercio</strong>.
        </li>
      </ul>
      <p>
        La revocatoria y la supresión no proceden cuando exista un deber legal o
        contractual de conservar el dato: los soportes de una compra deben guardarse por
        el término que fijan la ley comercial y la tributaria, aunque cierres tu cuenta.
        Tampoco proceden mientras una reclamación esté en trámite.
      </p>
      <p>
        <strong>
          Antes de quejarte ante la Superintendencia debes escribirnos primero.
        </strong>{" "}
        El artículo 16 de la Ley 1581 de 2012 exige haber agotado la consulta o el reclamo
        ante nosotros como requisito para elevar la queja.
      </p>

      <h2>8. Cómo ejercerlos</h2>
      <p>
        Escribe a <strong>[correo]</strong> indicando tu nombre, el dato que quieres
        consultar o corregir, los hechos que motivan tu solicitud, una dirección de
        contacto y los documentos que quieras hacer valer. Los plazos legales son:
      </p>
      <ul>
        <li>
          <strong>Consultas:</strong> hasta diez (10) días hábiles, prorrogables por cinco
          (5) más avisándote los motivos de la demora.
        </li>
        <li>
          <strong>Reclamos:</strong> hasta quince (15) días hábiles contados desde el día
          siguiente al recibo, prorrogables por ocho (8) más avisándote los motivos.
        </li>
      </ul>
      <p>Además, en el trámite de un reclamo:</p>
      <ul>
        <li>
          Si tu reclamo está incompleto te lo diremos dentro de los cinco (5) días
          siguientes para que lo subsanes. Si pasan dos (2) meses sin que envíes lo
          pedido, se entiende que desististe.
        </li>
        <li>
          Si el reclamo no es de nuestra competencia, lo trasladaremos a quien corresponda
          en un máximo de dos (2) días hábiles y te lo informaremos.
        </li>
        <li>
          Mientras se decide, el dato queda marcado con la leyenda «reclamo en trámite» en
          un plazo no mayor a dos (2) días hábiles.
        </li>
      </ul>

      <h2>9. Cómo los protegemos</h2>
      <ul>
        <li>
          Las contraseñas se guardan con un algoritmo de un solo sentido que impide
          recuperarlas.
        </li>
        <li>Las cuentas bancarias se almacenan cifradas.</li>
        <li>
          El acceso está restringido por perfil: cada quien ve solo lo que le corresponde.
        </li>
        <li>Las acciones administrativas sensibles quedan registradas con su autor.</li>
        <li>Los documentos privados solo se abren mediante un enlace temporal.</li>
        <li>
          A las fotografías que subes les eliminamos los metadatos, incluidas las
          coordenadas que muchas cámaras y teléfonos guardan dentro de la imagen.
        </li>
        <li>La comunicación con la plataforma viaja cifrada.</li>
      </ul>
      <p>
        Ninguna medida elimina por completo el riesgo. Si ocurriera un incidente que
        afecte tus datos —una violación de los códigos de seguridad, una pérdida o un
        acceso no autorizado—, te informaremos y{" "}
        <strong>
          lo reportaremos a la Superintendencia de Industria y Comercio dentro de los
          quince (15) días hábiles siguientes
        </strong>{" "}
        a su detección, en los términos de la Circular Única de esa entidad.
      </p>

      <h2>10. Cuánto tiempo los conservamos</h2>
      <p>
        Conservamos tus datos mientras tu cuenta esté activa y mientras subsistan las
        finalidades descritas en el apartado 4. Después:
      </p>
      <ul>
        <li>
          <strong>Soportes de compras, facturación y liquidaciones:</strong> diez (10)
          años contados desde el último asiento o comprobante, por el término que exige la
          ley comercial para los libros y papeles del comerciante.
        </li>
        <li>
          <strong>Registros de auditoría y seguridad:</strong> [plazo definido por la
          empresa].
        </li>
        <li>
          <strong>Los demás datos de la cuenta:</strong> [plazo definido por la empresa]
          después del cierre.
        </li>
      </ul>
      <p>
        Cumplido el término, los datos se eliminan o se anonimizan de forma que ya no
        puedan asociarse contigo.
      </p>
      <p>
        <strong>Período de vigencia de las bases de datos:</strong> las bases de datos de
        MONK GRAIN se mantendrán vigentes mientras la empresa desarrolle su objeto social
        y sea necesario para las finalidades aquí descritas.
      </p>

      <h2>11. Menores de edad</h2>
      <p>
        La plataforma no está dirigida a menores de edad y no recogemos deliberadamente
        sus datos. La Ley 1581 de 2012 proscribe el tratamiento de datos de niñas, niños y
        adolescentes, salvo los de naturaleza pública, y exige que se respeten sus
        derechos prevalentes. Si detectamos una cuenta de un menor, la cerraremos y
        suprimiremos sus datos, salvo aquello que debamos conservar por mandato legal.
      </p>

      <h2>12. Registro Nacional de Bases de Datos</h2>
      <p>
        La obligación de inscribir las bases de datos en el Registro Nacional de Bases de
        Datos (RNBD) de la Superintendencia de Industria y Comercio recae, según el
        Decreto 090 de 2018, sobre las sociedades y entidades sin ánimo de lucro cuyos
        activos totales superen las 100.000 UVT y sobre las personas jurídicas de
        naturaleza pública.{" "}
        <strong>
          [Indicar si la empresa está o no obligada y, si lo está, la fecha de
          inscripción.]
        </strong>
      </p>

      <h2>13. Cambios</h2>
      <p>
        Si modificamos esta política te avisaremos por correo o mediante la plataforma
        antes de que empiece a regir. Los cambios sustanciales, en especial los que
        afecten la finalidad del tratamiento, requerirán una nueva autorización tuya.
      </p>

      <hr />
      <p className="text-sm text-muted-foreground">
        Ver también la <Link href="/legal/privacidad">política de privacidad</Link> y los{" "}
        <Link href="/legal/terminos">términos y condiciones</Link>.
      </p>
    </>
  );
}
