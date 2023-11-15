package com.github.kam1sh.statistics

import io.ktor.http.*
import io.ktor.serialization.kotlinx.json.*
import io.ktor.server.application.*
import io.ktor.server.plugins.callloging.*
import io.ktor.server.plugins.contentnegotiation.*
import io.ktor.server.request.*
import io.ktor.server.response.*
import io.ktor.server.routing.*
import io.opentelemetry.api.OpenTelemetry
import io.opentelemetry.api.trace.propagation.W3CTraceContextPropagator
import io.opentelemetry.context.propagation.ContextPropagators
import io.opentelemetry.exporter.otlp.http.trace.OtlpHttpSpanExporter
import io.opentelemetry.instrumentation.ktor.v2_0.server.KtorServerTracing
import io.opentelemetry.sdk.OpenTelemetrySdk
import io.opentelemetry.sdk.resources.Resource
import io.opentelemetry.sdk.trace.SdkTracerProvider
import io.opentelemetry.sdk.trace.export.BatchSpanProcessor
import io.opentelemetry.semconv.ResourceAttributes
import kotlinx.serialization.ExperimentalSerializationApi
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonNames
import org.slf4j.LoggerFactory

private val bodyLog = LoggerFactory.getLogger("com.github.kam1sh.statistics.body")


@Serializable
@OptIn(ExperimentalSerializationApi::class)
data class System(
    val id64: Long,
    val name: String,
    val coords: Coords,
    val bodyCount: Int = 0,
    val date: String,
    @JsonNames("bodies")
    private val _bodies: List<Body>
) {
    val bodies get() = _bodies.map {
        if (it.name == name) it else it.copy(name = it.name.substringAfter(name).trim())
    }
    val log = LoggerFactory.getLogger(javaClass)
}

fun System.process(): SystemInformation {
    log.info("Processing system {}", name)
    val stats = bodies.process()
    return stats.copy()
}

@Serializable
data class Coords(val x: Double, val y: Double, val z: Double)

@Serializable
data class Station(
    val name: String,
    val primaryEconomy: String,
    val controllingFaction: String
)

@Serializable
data class Body(
    val id64: Long,
    val name: String,
    val type: String,
    val subType: String? = null,
    val terraformingState: String? = null,
    val stations: List<Station>,
)

@Serializable
data class SystemInformation(
    val name: String,
    val planets: PlanetStats,
    val stations: List<Station>,
)

@Serializable
data class PlanetStats(
    val total: Int,
    val byType: Map<String, Int>,
    val hasTerraformable: Boolean
)

fun List<Body>.process(): SystemInformation {
    val planets = filter { it.subType != null }
    val byType = planets.groupBy { it.subType ?: "unknown" }.mapValues { it.value.size }
    byType.forEach {
        bodyLog.info("amount of '{}': {}", it.key, it.value)
    }
    forEach {
        bodyLog.info("Body {} has subType {}", it.name, it.subType)
        if ("Black Hole" in byType) bodyLog.error("what to do with black holes?")
    }
    return SystemInformation(
        name = "",
        planets = PlanetStats(
            total = planets.size,
            byType = byType,
            hasTerraformable = any { it.terraformingState == "Terraformable" }
        ),
        stations = flatMap { it.stations }
    )
}

fun main(args: Array<String>): Unit = io.ktor.server.netty.EngineMain.main(args)

@Suppress("unused")
fun Application.module(testing: Boolean = false) {
    install(CallLogging)
    install(ContentNegotiation) {
        json(json = Json {
            ignoreUnknownKeys = true
        })
    }

    val otelSdk = otel()

    install(KtorServerTracing) {
        setOpenTelemetry(otelSdk)
    }

    val log = LoggerFactory.getLogger("com.github.kam1sh.statistics")
    log.info("Starting...")

    routing {
        post {
            val sys = call.receive<System>()
            val info = sys.process()
            call.respond(info)
        }
    }
}

fun otel(): OpenTelemetry {
    val resource = Resource.getDefault().toBuilder()
        .put(ResourceAttributes.SERVICE_NAME, "statistics")
        .put(ResourceAttributes.SERVICE_VERSION, "0.1.0")
        .build()
    val provider = SdkTracerProvider.builder()
        .addSpanProcessor(BatchSpanProcessor.builder(
            OtlpHttpSpanExporter.builder()
                .setEndpoint("http://tempo:4318/v1/traces")
                .build()
        ).build())
        .addResource(resource)
        .build()
    return OpenTelemetrySdk.builder()
        .setTracerProvider(provider)
        .setPropagators(ContextPropagators.create(W3CTraceContextPropagator.getInstance()))
        .buildAndRegisterGlobal()
}
