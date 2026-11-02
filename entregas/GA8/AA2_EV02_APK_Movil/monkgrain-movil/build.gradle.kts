// Los complementos se declaran aquí con `apply false` y se aplican en el
// módulo. Así la versión está en un solo sitio y no puede divergir entre
// módulos cuando el proyecto crezca.
plugins {
    id("com.android.application") version "8.5.2" apply false
    id("org.jetbrains.kotlin.android") version "1.9.24" apply false
    id("org.jetbrains.kotlin.plugin.serialization") version "1.9.24" apply false
}
