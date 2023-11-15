import org.jetbrains.kotlin.gradle.tasks.KotlinCompile

plugins {
    kotlin("jvm") version "1.9.20"
    kotlin("plugin.serialization") version "1.9.20"
    application
}

group = "com.github.kam1sh.statistics"
version = "1.0-SNAPSHOT"

repositories {
    mavenCentral()
}

val ktor_version = "2.3.6"
dependencies {
    implementation(kotlin("stdlib-jdk8"))
    implementation("io.ktor:ktor-server-netty:$ktor_version")
    implementation("io.ktor:ktor-server-call-id:$ktor_version")
    implementation("io.ktor:ktor-server-call-logging:$ktor_version")
    implementation("io.ktor:ktor-server-content-negotiation:$ktor_version")
    implementation("io.ktor:ktor-serialization-kotlinx-json:$ktor_version")

    val otel_version = "1.31.0"
    implementation("io.opentelemetry:opentelemetry-api:$otel_version");
    implementation("io.opentelemetry:opentelemetry-sdk:$otel_version");
    implementation("io.opentelemetry:opentelemetry-sdk-metrics:$otel_version");
    implementation("io.opentelemetry:opentelemetry-semconv:1.30.1-alpha");
    implementation("io.opentelemetry.instrumentation:opentelemetry-ktor-2.0:1.31.0-alpha")
    implementation("io.opentelemetry:opentelemetry-exporter-otlp:$otel_version")

    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.5.1")

    implementation("org.slf4j:slf4j-api:2.0.7")
    implementation("ch.qos.logback:logback-classic:1.4.6")

}

tasks.test {
    useJUnitPlatform()
}

tasks.named<JavaExec>("run") {
    standardInput = System.`in`
}

kotlin {
    jvmToolchain(8)
}

application {
    mainClass.set("com.github.kam1sh.statistics.MainKt")
    val isDevelopment: Boolean = project.ext.has("development")
    applicationDefaultJvmArgs = listOf("-Dio.ktor.development=$isDevelopment")
}