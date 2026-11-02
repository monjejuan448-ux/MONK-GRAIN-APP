# Los DTO se leen por reflexion desde kotlinx.serialization. Sin estas
# reglas, la version de release ofusca sus nombres de campo y la lectura del
# JSON falla SOLO en release: en debug funciona, porque ahi no hay ofuscacion.
# Es el error mas desconcertante de Android, porque aparece cuando ya se
# dio el trabajo por terminado.
-keepattributes *Annotation*, InnerClasses
-dontnote kotlinx.serialization.**

-keepclassmembers class co.monkgrain.movil.data.dto.** {
    *** Companion;
    <fields>;
}
-keepclasseswithmembers class co.monkgrain.movil.data.dto.** {
    kotlinx.serialization.KSerializer serializer(...);
}
