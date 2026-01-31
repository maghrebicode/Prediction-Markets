plugins {
    kotlin("jvm") version "1.9.22"
    application
}

group = "com.kalshi"
version = "1.0.0"

repositories {
    mavenCentral()
}

dependencies {
    implementation("org.json:json:20231013")
}

application {
    mainClass.set("kalshi.MainKt")
}

tasks.jar {
    manifest {
        attributes["Main-Class"] = "kalshi.MainKt"
    }
    from(configurations.runtimeClasspath.get().map { if (it.isDirectory) it else zipTree(it) })
    duplicatesStrategy = DuplicatesStrategy.EXCLUDE
}

kotlin {
    jvmToolchain(17)
}
