import os
import json

from flask import Flask, request
from attrs import asdict, define
from kafka import KafkaProducer

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

resource = Resource(attributes={
    SERVICE_NAME: "storage"
})
provider = TracerProvider(resource=resource)
exporter = OTLPSpanExporter("http://tempo:4318/v1/traces")
processor = BatchSpanProcessor(exporter)
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

@define
class Station:
    name: str
    primary_economy: str
    controlling_faction: str

    @classmethod
    def from_dict(cls, d):
        return cls(
            name=d["name"],
            primary_economy=d["primaryEconomy"],
            controlling_faction=d["controllingFaction"]
        )

@define
class PlanetStats:
    total: int
    by_type: dict[str, int]
    has_terraformable: bool

    @classmethod
    def from_dict(cls, d):
        return cls(
            total=d["total"],
            by_type=d["byType"],
            has_terraformable=d["hasTerraformable"]
        )

@define
class SystemInformation:
    name: str
    planets: PlanetStats
    stations: list[Station]

    @classmethod
    def from_dict(cls, d):
        planets = PlanetStats.from_dict(d["planets"])
        stations = [Station.from_dict(x) for x in d["stations"]]
        return cls(
            name=d["name"],
            planets=planets,
            stations=stations
        )

producer = KafkaProducer(bootstrap_servers=os.environ["STORAGE_KAFKA_SERVERS"])

app = Flask("storage")
FlaskInstrumentor().instrument_app(app, tracer_provider=provider)

@app.route("/", methods=["POST"])
def store():
    data = SystemInformation.from_dict(request.json)
    serialized = json.dumps(asdict(data)).encode()
    producer.send("system_infos", serialized)
    return "Ok."

