import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Devoluciones y reembolsos",
  description:
    "Cómo solicitar una devolución, hacer efectiva la garantía o pedir la reversión del " +
    "pago en MONK GRAIN, conforme al Estatuto del Consumidor colombiano.",
};

export default function ReturnsPage() {
  return (
    <>
      <h1>Devoluciones y reembolsos</h1>
      <p className="text-sm text-muted-foreground">
        Vigente desde [fecha] · Última actualización: [fecha]
      </p>

      <h2>1. Tres caminos distintos</h2>
      <p>
        La ley colombiana te da tres herramientas diferentes, y conviene no confundirlas
        porque tienen plazos y consecuencias distintas:
      </p>
      <ul>
        <li>
          <strong>El retracto:</strong> te arrepentiste de la compra. No necesitas dar
          explicaciones, pero el café debe volver sin abrir.
        </li>
        <li>
          <strong>La garantía legal:</strong> el café llegó mal, vencido, dañado o no es
          el que pediste. Aquí sí hay un problema con el producto.
        </li>
        <li>
          <strong>La reversión del pago:</strong> el dinero vuelve a tu tarjeta a través
          de tu banco, sin esperar a que el vendedor lo devuelva.
        </li>
      </ul>
      <p>
        Puedes usar más de uno. Pedir la garantía no te quita el derecho a solicitar la
        reversión del pago, ni al contrario.
      </p>

      <h2>2. Derecho de retracto</h2>
      <p>
        En las compras a distancia, el <strong>artículo 47 de la Ley 1480 de 2011</strong>{" "}
        (Estatuto del Consumidor) te permite retractarte dentro de los{" "}
        <strong>cinco (5) días hábiles</strong> siguientes a la entrega del café, sin
        tener que justificar el motivo. Ejercido el retracto, el contrato se resuelve y se
        te devuelve el dinero.
      </p>
      <p>
        La ley exige que devuelvas el producto{" "}
        <strong>
          por los mismos medios y en las mismas condiciones en que lo recibiste
        </strong>
        . Tratándose de café, eso significa que la bolsa debe volver{" "}
        <strong>sellada, sin abrir</strong> y con su empaque original.
      </p>
      <p>
        <strong>Los costos de transporte de la devolución los asume el comprador.</strong>{" "}
        Así lo dispone el mismo artículo 47. Esto solo aplica al retracto: si el reclamo
        es por un defecto, el transporte corre por cuenta de quien vende (numeral 1 del
        artículo 11 de la Ley 1480 de 2011).
      </p>
      <p>
        <strong>La devolución del dinero es completa</strong>, sin descuentos ni
        retenciones de ningún tipo, y no puede tardar más de{" "}
        <strong>treinta (30) días calendario</strong> contados desde el momento en que
        ejerciste el derecho, no desde que aprobamos la solicitud.
      </p>

      <h3>Por qué te lo damos aunque la ley no nos obligue</h3>
      <p>
        El artículo 47 excluye del retracto los bienes perecederos y los que por su
        naturaleza puedan deteriorarse o caducar con rapidez. El pergamino seco, guardado
        en bodega ventilada y con su humedad entre 10 % y 12 %, se conserva meses sin
        perder calidad: no es un bien que caduque con rapidez, de modo que{" "}
        <strong>el retracto sí te corresponde</strong> sobre el lote que devuelvas en las
        mismas condiciones en que lo recibiste.
      </p>
      <p>
        Lo que sí puede hacer que un lote deje de ser devolvible es su manejo: pergamino
        que se mojó, que se guardó sobre piso húmedo, que tomó olores de lo que estaba a
        su lado o que ya pasó por trilla no vuelve al inventario del vendedor.
      </p>
      <p>
        Lo que no podemos aceptar es un empaque abierto: el café es un alimento y una
        bolsa abierta no puede volver a venderse. Esto{" "}
        <strong>no limita en nada tu garantía</strong>: si el café llegó en mal estado,
        contaminado o no corresponde a lo que compraste, puedes reclamar aunque lo hayas
        abierto, y de hecho abrirlo suele ser la única forma de darse cuenta.
      </p>

      <h2>3. Garantía legal</h2>
      <p>
        La garantía legal es la obligación de responder por el buen estado del café y por
        su correspondencia con lo que se te ofreció.{" "}
        <strong>No tiene costo adicional</strong> y no depende de que la hayamos
        prometido: la impone la ley.
      </p>

      <h3>Hasta cuándo la tienes</h3>
      <p>
        El <strong>artículo 8 de la Ley 1480 de 2011</strong> establece que, tratándose de
        productos perecederos, el término de la garantía legal es{" "}
        <strong>el de la fecha de vencimiento o expiración</strong> impresa en el empaque.
        Si el café no indica fecha de vencimiento, el término es de{" "}
        <strong>un (1) año</strong> contado desde la entrega, por tratarse de un producto
        nuevo.
      </p>
      <p>
        Ninguna condición de esta página reduce ese término. Si en algún punto de la
        plataforma aparece un plazo menor, prevalece el legal.
      </p>

      <h3>En qué casos puedes reclamar</h3>
      <ul>
        <li>El empaque llegó roto, mojado o violado.</li>
        <li>
          El pergamino llegó húmedo, con moho, con olor a fermento o con signos de
          deterioro.
        </li>
        <li>Recibiste un lote distinto del que pediste.</li>
        <li>
          El lote no corresponde a lo publicado: otra variedad, otro proceso, menos kilos
          de los pagados, otro código de lote.
        </li>
        <li>
          El análisis no corresponde a lo declarado: un factor de rendimiento
          sensiblemente peor, más humedad, más pasilla o más broca de lo publicado.
        </li>
      </ul>
      <p>
        El análisis que publica el vendedor se hace sobre una muestra, y toda muestra
        tiene una tolerancia: una diferencia de medio punto de factor o de dos décimas de
        humedad no constituye por sí sola un incumplimiento. Otra cosa es una diferencia
        que cambia el valor del lote —tres puntos de factor, humedad por encima del 12 %,
        el doble de pasilla declarada—: eso sí lo es. Por eso conviene pedir muestra y
        hacer tu propio análisis antes de cerrar una compra por volumen.
      </p>

      <h3>Qué puedes pedir</h3>
      <p>
        Como el café no admite reparación, la garantía se hace efectiva mediante{" "}
        <strong>la reposición del producto o la devolución del dinero</strong>, a tu
        elección, junto con los costos de transporte que la devolución implique.
      </p>

      <h2>4. Si el pedido no llega o llega tarde</h2>
      <p>
        Salvo que se haya pactado otro plazo, el pedido debe entregarse{" "}
        <strong>a más tardar treinta (30) días calendario</strong> contados desde el día
        siguiente a aquel en que lo hiciste (literal h del artículo 50 de la Ley 1480 de
        2011). Si el café no está disponible, se te informará de inmediato.
      </p>
      <p>
        Superado ese plazo, o si el producto no está disponible,{" "}
        <strong>puedes terminar el contrato unilateralmente</strong> y recuperar todas las
        sumas pagadas, sin retención ni descuento alguno. La devolución se hace efectiva
        en un plazo máximo de treinta (30) días calendario.
      </p>

      <h2>5. Cómo presentar tu solicitud</h2>
      <ol>
        <li>Entra a tu cuenta y abre el pedido correspondiente.</li>
        <li>
          Elige «Solicitar devolución» e indica si te estás retractando o si reclamas por
          un defecto.
        </li>
        <li>
          Describe el problema e identifica el producto y la fecha de entrega. Adjunta
          fotografías del café y del empaque cuando el reclamo sea por defecto.
        </li>
      </ol>
      <p>
        También puedes escribir a <strong>[correo]</strong> o llamar al{" "}
        <strong>[teléfono]</strong> indicando el número de tu pedido. Puedes reclamar y
        devolver <strong>por los mismos medios de la compra original</strong>, como exige
        el numeral 2 del artículo 46 de la Ley 1480 de 2011.
      </p>
      <p>
        Recibirás siempre una <strong>constancia con la fecha y la hora</strong> de
        radicación y un número para hacerle seguimiento. Guarda esa constancia: la vas a
        necesitar si más adelante acudes a la autoridad.
      </p>

      <h2>6. Plazos de respuesta</h2>
      <ul>
        <li>
          <strong>Respuesta a tu reclamación de garantía:</strong> hasta{" "}
          <strong>quince (15) días hábiles</strong> desde que la presentas. La respuesta
          es escrita e indica si la reclamación procede o no, y por qué (Decreto 735 de
          2013).
        </li>
        <li>
          <strong>Devolución del dinero por garantía:</strong> a más tardar dentro de los{" "}
          <strong>quince (15) días hábiles</strong> siguientes a que pongas el café a
          disposición de quien vende.
        </li>
        <li>
          <strong>Devolución del dinero por retracto:</strong> hasta{" "}
          <strong>treinta (30) días calendario</strong> desde que ejerciste el derecho.
        </li>
      </ul>
      <p>
        El reembolso se hace por el mismo medio con el que pagaste, salvo que acuerdes
        otro contigo.
      </p>

      <h2>7. Reversión del pago</h2>
      <p>
        Si pagaste con tarjeta de crédito, débito o cualquier otro instrumento de pago
        electrónico, el <strong>artículo 51 de la Ley 1480 de 2011</strong> te da un
        camino adicional: pedirle a tu banco que reverse el pago. Procede cuando:
      </p>
      <ul>
        <li>Fuiste víctima de fraude.</li>
        <li>La operación no fue solicitada por ti.</li>
        <li>No recibiste el café.</li>
        <li>
          El café entregado no corresponde a lo solicitado o no cumple las características
          que se informaron sobre él.
        </li>
        <li>El café llegó defectuoso.</li>
      </ul>
      <p>Para que proceda debes hacer dos cosas dentro de los mismos plazos:</p>
      <ol>
        <li>
          <strong>Presentar la queja ante quien te vendió</strong>, dentro de los{" "}
          <strong>cinco (5) días hábiles</strong> siguientes a la fecha en que tuviste
          noticia del hecho o en que debiste haber recibido el café. En la misma queja
          indícale que el café queda a su disposición para que lo recoja, en el mismo
          lugar y en las mismas condiciones en que lo recibiste: con eso se entiende
          cumplida tu obligación de devolverlo.
        </li>
        <li>
          <strong>Notificar a tu banco o al emisor de tu medio de pago</strong>, dentro de
          ese mismo plazo de cinco (5) días hábiles, adjuntando la constancia de la queja.
        </li>
      </ol>
      <p>
        La queja debe indicar las razones, la causal invocada, el valor cuya reversión
        pides y la cuenta o tarjeta a la que se cargó la operación. Si la compra incluyó
        varios cafés, puedes pedir la reversión solo del que tuvo el problema. Una vez
        notificado el emisor, los participantes del proceso de pago tienen{" "}
        <strong>quince (15) días hábiles</strong> para hacer efectiva la reversión
        (Decreto 587 de 2016, hoy compilado en el Decreto 1074 de 2015).
      </p>
      <p>
        Ten en cuenta que si después una autoridad judicial o administrativa decide que la
        reversión no procedía, el valor se te vuelve a cargar y quedas a cargo de los
        costos que haya generado.
      </p>
      <p className="rounded-md border border-border bg-muted/40 p-3 text-sm">
        <strong>Estado actual:</strong> la plataforma opera hoy con un proveedor de pago{" "}
        <strong>simulado</strong>, sin cobro real de dinero, por lo que todavía no hay
        instrumento de pago electrónico que reversar. Este apartado empezará a aplicarse
        cuando se active una pasarela con cobro efectivo.
      </p>

      <h2>8. Cancelar antes del despacho</h2>
      <p>
        Mientras el pedido no haya sido despachado puedes cancelarlo desde tu cuenta sin
        costo alguno, y el inventario vuelve al catálogo de inmediato. Una vez despachado
        ya no puede cancelarse, pero siguen abiertos los caminos del retracto, la garantía
        y la reversión del pago.
      </p>

      <h2>9. Quién responde</h2>
      <p>
        La venta se celebra entre el comprador y quien vende, y es{" "}
        <strong>quien vende</strong> el obligado directo a atender la garantía y a
        devolver el dinero. MONK GRAIN recibe la solicitud, la traslada, hace seguimiento
        y, cuando la reclamación procede y quien vende no responde, puede retener o
        descontar el valor en su liquidación para protegerte.
      </p>
      <p>
        Dicho esto,{" "}
        <strong>
          nada de lo escrito aquí limita ni traslada las responsabilidades que la ley
          colombiana nos imponga
        </strong>
        . El artículo 10 de la Ley 1480 de 2011 establece que la responsabilidad por la
        garantía legal recae solidariamente en productores y proveedores, y el artículo 43
        de la misma ley declara ineficaz de pleno derecho cualquier cláusula que limite
        esa responsabilidad o que la traslade a un tercero. Si una autoridad concluye que
        MONK GRAIN debe responder frente a ti, responderá.
      </p>

      <h2>10. Si no llegamos a un acuerdo</h2>
      <p>
        Puedes acudir a la <strong>Superintendencia de Industria y Comercio</strong>, que
        es la autoridad competente en protección al consumidor en Colombia:{" "}
        <a href="https://www.sic.gov.co" target="_blank" rel="noopener noreferrer">
          www.sic.gov.co
        </a>
        . También es competente el juez del lugar donde adquiriste el café o donde se
        realizó la relación de consumo, y no necesitas abogado para actuar.
      </p>
      <p>
        Para presentar la acción de protección al consumidor deberás acompañar la
        constancia de la reclamación que nos hiciste, así que conserva el número de
        radicación. Las demandas para hacer efectiva la garantía deben presentarse, a más
        tardar, dentro del año siguiente a la expiración de la garantía.
      </p>

      <hr />
      <p className="text-sm text-muted-foreground">
        Ver también los <Link href="/legal/terminos">términos y condiciones</Link> y la{" "}
        <Link href="/legal/datos">política de tratamiento de datos</Link>.
      </p>
    </>
  );
}
