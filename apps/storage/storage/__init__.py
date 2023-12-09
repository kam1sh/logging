from logging import LogRecord
import os
import json
import logging
import collections

from flask import Flask, request
from attrs import asdict, define
from kafka import KafkaProducer
from loguru import logger

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
    def from_dict(cls, items):
        by_type = collections.defaultdict(lambda: 0)
        for x in items:
            by_type[x["subType"]] += 1
        return cls(
            total=len(items),
            by_type=by_type,
            has_terraformable=any(x["terraformingState"] != "Not terraformable" for x in items)
        )

@define
class SystemInformation:
    name: str
    planets: PlanetStats
    stations: list[Station]

    @classmethod
    def from_dict(cls, d):
        planets = filter(lambda x: x["type"] == "Planet", d["bodies"])
        planets = PlanetStats.from_dict(list(planets))
        stations = [Station.from_dict(x) for x in d["stations"]]
        return cls(
            name=d["name"],
            planets=planets,
            stations=stations
        )

producer = KafkaProducer(bootstrap_servers=os.environ["STORAGE_KAFKA_SERVERS"])


class LoguruHandler(logging.Handler):
    def emit(self, record: LogRecord) -> None:
        logger_opt = logger.opt(depth=6, exception=record.exc_info)
        logger_opt.log(record.levelno, record.getMessage())

app = Flask(__name__)
logging.root.handlers = [LoguruHandler()]
logger.remove(0)
logger.add("/logs/storage.json", format="{message}", serialize=True)

@app.route("/", methods=["POST"])
def store():
    data = SystemInformation.from_dict(request.json)
    serialized = json.dumps(asdict(data)).encode()
    producer.send("system_infos", serialized)
    return "Ok."

