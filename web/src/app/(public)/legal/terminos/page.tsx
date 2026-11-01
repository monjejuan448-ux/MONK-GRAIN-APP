import { COMMISSION_LABEL } from "@/lib/business";
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Términos y condiciones",
  description:
    "Condiciones de uso de MONK GRAIN, el marketplace que conecta caficultores colombianos " +
    "con compradores.",
};

export default function TermsPage() {
  return (
    <>
      <h1>Términos y condiciones</h1>
      <p className="text-sm text-muted-foreground">
        Vigente desde [fecha] · Última actualización: [fecha]
      </p>

      <h2>1. Quiénes somos</h2>
      <p>MONK GRAIN es una plataforma operada por:</p>
      <ul>
        <li>
          <strong>Razón social:</strong> [Razón social]
        </li>
        <li>
          <strong>NIT:</strong> [número]
        </li>
        <li>
          <strong>Domicilio y dirección de notificación judicial:</strong> [dirección],
          [ciudad], Colombia
        </li>
        <li>
          <strong>Teléfono:</strong> [teléfono]
        </li>
        <li>
          <strong>Correo electrónico:</strong> [correo]
        </li>
      </ul>
      <p>
        Ponemos en contacto a caficultores, fincas, cooperativas y tostadores colombianos
        con quienes quieren comprar su café pergamino seco.{" "}
        <strong>Somos un intermediario tecnológico:</strong> no cultivamos, no trillamos,
        no analizamos ni almacenamos café. Cada venta se celebra entre el comprador y el
        vendedor.
      </p>
      <p>
        La plataforma es un <strong>portal de contacto</strong> en el sentido del artículo
        53 de la Ley 1480 de 2011, y como tal asumimos los deberes que esa norma nos
        impone. Puedes ver cuáles en el apartado 11.
      </p>

      <h2>2. Alcance del servicio</h2>
      <p>
        La plataforma opera <strong>únicamente en territorio colombiano</strong>: los
        precios se expresan en pesos colombianos (COP) y los envíos se realizan a
        direcciones dentro de Colombia.
      </p>
      <p>
        Aceptar estos términos equivale a firmarlos. La Ley 527 de 1999 reconoce validez y
        fuerza obligatoria a los acuerdos celebrados por medios electrónicos, y guardamos
        constancia de tu aceptación.
      </p>

      <h2>3. Tu cuenta</h2>
      <ul>
        <li>
          Debes ser <strong>mayor de edad</strong> y aportar información veraz. La
          plataforma no está dirigida a menores; si detectamos una cuenta de un menor sin
          autorización de sus representantes, la cerraremos (artículo 52 de la Ley 1480 de
          2011).
        </li>
        <li>
          Eres responsable de tu contraseña y de lo que ocurra con tu cuenta. Avísanos si
          sospechas que alguien más accedió a ella.
        </li>
        <li>
          Podemos suspender o cerrar una cuenta que incumpla estos términos.{" "}
          <strong>Siempre te informaremos el motivo</strong> y tendrás la oportunidad de
          explicarte.
        </li>
      </ul>
      <p>
        Una suspensión{" "}
        <strong>no afecta el dinero que ya pagaste ni los pedidos en curso</strong>: los
        pedidos confirmados se despachan o se reembolsan, y las liquidaciones pendientes a
        favor de un vendedor se pagan. Tampoco te priva de reclamar la garantía de lo que
        ya compraste.
      </p>

      <h2>4. Si vendes en la plataforma</h2>
      <p>
        Para vender debes solicitar la habilitación como vendedor y superar nuestra
        revisión. Al publicar un café te comprometes a que:
      </p>
      <ul>
        <li>La información sobre origen, variedad, proceso y perfil sea veraz.</li>
        <li>
          Solo declares certificaciones que{" "}
          <strong>tengas realmente y estén vigentes</strong>, con su documento de
          respaldo.
        </li>
        <li>El inventario publicado corresponda a existencias reales.</li>
        <li>Despaches dentro del plazo que anunciaste.</li>
        <li>
          El producto cumpla la normativa sanitaria y de etiquetado aplicable a los
          alimentos empacados, y que cuentes con los permisos, registros o notificaciones
          sanitarias que exija el INVIMA para tu caso.
        </li>
        <li>
          Solo uses la denominación de origen «Café de Colombia» u otras denominaciones
          protegidas si estás autorizado para hacerlo.
        </li>
      </ul>
      <p>
        Como vendedor eres el <strong>proveedor</strong> frente al comprador: responder
        por la calidad, la idoneidad, la conformidad, la garantía legal y la entrega del
        café es tu obligación, y también lo es{" "}
        <strong>expedir la factura electrónica de venta</strong> al comprador. La
        plataforma pone a tu disposición el medio para emitirla y entregarla, pero la
        obligación de facturar es de quien vende. Podemos retirar del catálogo
        publicaciones con información falsa o engañosa.
      </p>
      <p>
        Al solicitar la habilitación aceptas entregarnos y mantener actualizados tu nombre
        o razón social, número de documento o NIT, dirección física de notificaciones y
        teléfono, y aceptas que esa información se entregue a un comprador tuyo que
        necesite presentarte una queja o reclamo, y a la autoridad competente cuando la
        solicite. Es una obligación que nos impone el artículo 53 de la Ley 1480 de 2011 y
        de la que no podemos eximirte.
      </p>

      <h3>Comisión</h3>
      <p>
        MONK GRAIN cobra una comisión del <strong>{COMMISSION_LABEL}</strong> calculada
        sobre el{" "}
        <strong>valor de los productos</strong> de cada venta confirmada,{" "}
        <strong>sin incluir el costo de envío</strong>. Se calcula al confirmarse el pago,
        queda registrada en tu liquidación y se descuenta del monto a transferir. Por esa
        comisión te expediremos la factura que corresponda.
      </p>
      <p>
        Cualquier cambio en la comisión se avisará con antelación y{" "}
        <strong>no afectará pedidos ya realizados</strong> ni liquidaciones pendientes.
      </p>

      <h2>5. Si compras en la plataforma</h2>
      <ul>
        <li>
          Los precios se informan{" "}
          <strong>en pesos colombianos e incluyen los impuestos</strong> y costos que
          debes pagar para adquirir el café. Los{" "}
          <strong>gastos de envío se informan por separado</strong>, antes de que pagues.
        </li>
        <li>
          Cada ficha de café indica su disponibilidad, el plazo de despacho y el tiempo
          durante el cual se mantiene la oferta.
        </li>
        <li>
          Antes de finalizar la compra verás un <strong>resumen del pedido</strong> con
          cada producto, su precio individual, los gastos de envío y el total a pagar.
          Puedes corregirlo o cancelar la transacción hasta antes de concluirla, y puedes
          imprimirlo o descargarlo.
        </li>
        <li>
          El pedido queda en firme cuando se confirma el pago. A más tardar{" "}
          <strong>el día calendario siguiente</strong> recibirás un acuse de recibo con el
          número de pedido, el tiempo de entrega, el precio exacto con impuestos, los
          gastos de envío y la forma en que se realizó el pago.
        </li>
        <li>
          Un carrito con cafés de varios vendedores genera{" "}
          <strong>un envío por cada uno</strong>, y cada quien despacha por separado. La
          garantía y las devoluciones se tramitan frente a cada vendedor.
        </li>
        <li>
          El análisis del pergamino —factor de rendimiento, humedad, almendra sana,
          pasilla, broca y granulometría— <strong>lo declara el vendedor</strong> sobre
          una muestra de su lote. MONK GRAIN no lo verifica ni lo certifica, y toda
          medición sobre muestra tiene una tolerancia. Pide muestra y haz tu propio
          análisis antes de cerrar una compra por volumen.
        </li>
        <li>
          El código SICA del predio se publica tal como lo declara el vendedor. No lo
          contrastamos con la Federación Nacional de Cafeteros.
        </li>
      </ul>
      <p>
        <strong>
          Nunca daremos por aceptado algo con tu silencio ni presumiremos tu voluntad
        </strong>{" "}
        cuando de ello se derive un cobro o una obligación a tu cargo.
      </p>
      <p>
        Tus derechos de retracto, garantía legal y reversión del pago, con sus plazos y su
        procedimiento, están explicados en la{" "}
        <Link href="/legal/devoluciones">política de devoluciones</Link>.
      </p>

      <h2>6. Pagos y facturación</h2>
      <p>
        Los pagos se procesan mediante una pasarela certificada.{" "}
        <strong>
          MONK GRAIN no almacena números de tarjeta ni códigos de seguridad.
        </strong>{" "}
        Los medios de pago disponibles se indican en el proceso de compra.
      </p>
      <p>
        La factura electrónica de venta del café la expide el vendedor. MONK GRAIN factura
        únicamente su comisión al vendedor.
      </p>
      <p className="rounded-md border border-border bg-muted/40 p-3 text-sm">
        <strong>Estado actual:</strong> la plataforma opera con un proveedor de pago{" "}
        <strong>simulado</strong>, sin cobro real de dinero. Este apartado regirá cuando
        se active una pasarela con cobro efectivo.
      </p>

      <h2>7. Envíos y plazos de entrega</h2>
      <p>
        El despacho corre por cuenta del vendedor, dentro del plazo indicado en cada café.
        El costo de envío se muestra antes de confirmar el pedido. Los tiempos de entrega
        dependen del operador logístico y del destino.
      </p>
      <p>
        Salvo que se pacte otro plazo,{" "}
        <strong>
          el pedido debe entregarse dentro de los treinta (30) días calendario
        </strong>{" "}
        siguientes al día en que lo hiciste. Si no está disponible, se te informará de
        inmediato. Superado ese plazo puedes terminar el contrato y recuperar todo lo
        pagado, sin descuentos, en un máximo de treinta (30) días calendario.
      </p>

      <h2>8. Peticiones, quejas y reclamos</h2>
      <p>
        Puedes radicar peticiones, quejas y reclamos desde tu cuenta o escribiendo a
        [correo].{" "}
        <strong>Siempre te entregaremos constancia de la fecha y la hora</strong> de
        radicación y un número para hacerle seguimiento.
      </p>
      <p>
        Conservamos la prueba de cada relación comercial —tu identidad, tu voluntad
        expresa de contratar, la forma en que se realizó el pago y la entrega efectiva del
        café— por el mismo tiempo por el que la ley obliga a guardar los documentos de
        comercio.
      </p>

      <h2>9. Reseñas</h2>
      <p>
        Solo puede reseñar quien compró el café, y una vez por compra. No se admiten
        reseñas con lenguaje ofensivo, datos personales de terceros o contenido ajeno al
        producto. Podemos retirar las que incumplan esta regla, informándote el motivo.
      </p>

      <h2>10. Propiedad intelectual</h2>
      <p>
        La marca, el diseño y el software de MONK GRAIN nos pertenecen. Los textos y
        fotografías que publica cada vendedor <strong>siguen siendo suyos</strong>.
      </p>
      <p>
        Al publicarlos nos autoriza, de forma gratuita y no exclusiva, a mostrarlos{" "}
        <strong>en la plataforma y en la difusión del catálogo</strong> mientras la
        publicación esté activa. La autorización termina cuando el vendedor retira la
        publicación o cierra su cuenta, salvo lo ya impreso o publicado antes de ese
        momento. Quien publica declara ser titular de esos contenidos o contar con permiso
        para usarlos.
      </p>

      <h2>11. Nuestro papel y nuestra responsabilidad</h2>
      <p>Como portal de contacto, MONK GRAIN se obliga a:</p>
      <ul>
        <li>
          Exigir a todo vendedor información que permita identificarlo, y llevar un
          registro con su nombre o razón social, documento de identificación, dirección
          física de notificaciones y teléfono.
        </li>
        <li>
          Poner esa información a disposición de quien compró un café y necesite presentar
          una queja o reclamo, y de la autoridad competente cuando la solicite.
        </li>
        <li>
          Adoptar mecanismos de seguridad apropiados y confiables para proteger tu
          información personal y las transacciones.
        </li>
      </ul>
      <p>
        Respondemos por el funcionamiento de la plataforma y por la seguridad de las
        transacciones realizadas por los medios que ponemos a disposición, sean propios o
        contratados con terceros. La calidad del café, su conformidad y el cumplimiento de
        la entrega son de cargo del vendedor. No garantizamos disponibilidad
        ininterrumpida: puede haber mantenimientos o fallas.
      </p>
      <p>
        <strong>
          Ninguna cláusula de estos términos limita, excluye ni traslada las
          responsabilidades que la ley colombiana nos impone
        </strong>
        , ni restringe los derechos que el Estatuto del Consumidor (Ley 1480 de 2011)
        reconoce a los consumidores. Cualquier estipulación que produzca ese efecto es
        ineficaz de pleno derecho, según los artículos 42 y 43 de esa ley, y se tendrá por
        no escrita sin que ello afecte el resto del contrato.
      </p>

      <h2>12. Comunicaciones</h2>
      <p>
        Los correos sobre tus pedidos, tu cuenta y tu seguridad forman parte del servicio.{" "}
        <strong>
          Las comunicaciones comerciales o publicitarias solo se envían por los canales
          que hayas autorizado expresamente
        </strong>
        , y puedes revocar esa autorización en cualquier momento desde tu cuenta o
        pidiéndolo a [correo], conforme a la Ley 2300 de 2023.
      </p>

      <h2>13. Cambios</h2>
      <p>
        Podemos modificar estos términos avisando con antelación por correo o mediante la
        plataforma.{" "}
        <strong>
          Los pedidos ya realizados se rigen por la versión vigente cuando se hicieron.
        </strong>
      </p>
      <p>
        Cuando el cambio implique nuevas obligaciones o cobros a tu cargo,{" "}
        <strong>necesitaremos tu aceptación expresa</strong>: tu silencio no se entenderá
        como consentimiento. Si no aceptas, puedes cerrar tu cuenta sin costo y sin más
        requisitos que los que se te pidieron para abrirla.
      </p>

      <h2>14. Ley aplicable y autoridades</h2>
      <p>
        Estos términos se rigen por la ley colombiana. Para efectos de notificaciones y de
        las controversias que no sean de consumo, se acuerda la competencia de los jueces
        de [ciudad], Colombia.
      </p>
      <p>
        <strong>Esto no restringe tus derechos como consumidor.</strong> Puedes acudir a
        la <strong>Superintendencia de Industria y Comercio</strong> —
        <a href="https://www.sic.gov.co" target="_blank" rel="noopener noreferrer">
          www.sic.gov.co
        </a>
        —, que tiene competencia en todo el territorio nacional, o al juez del lugar donde
        adquiriste el café o donde se realizó la relación de consumo, y no necesitas
        abogado para hacerlo.
      </p>

      <h2>15. Contacto</h2>
      <p>Escríbenos a [correo] o al [teléfono].</p>

      <hr />
      <p className="text-sm text-muted-foreground">
        Ver también la <Link href="/legal/devoluciones">política de devoluciones</Link> y
        el <Link href="/legal/datos">tratamiento de datos personales</Link>.
      </p>
    </>
  );
}
