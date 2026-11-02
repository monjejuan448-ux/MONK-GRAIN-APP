// MONK GRAIN móvil — GA8-220501096-AA2-EV02
//
// `repositories` va aquí y no en cada módulo: desde Gradle 7, declararlos en
// `settings` impide que un módulo añada un repositorio por su cuenta, que es
// por donde entra una dependencia de procedencia desconocida.
pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "MONK GRAIN movil"
include(":app")
