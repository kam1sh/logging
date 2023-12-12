import asyncio
from pathlib import Path

from o11y_tests.container import ContainerRunner

class Fluentbit:
    def __init__(self, network, config_name, extra_vols=None) -> None:
        project_root = Path().resolve().parents[0]
        pth = project_root / "logging" / "fluent-bit"
        volumes = {
            str(project_root / "logs"): "/logs",
            str(pth / "parser.conf"): "/parser.conf",
            str(pth / config_name): "/fluent-bit.yaml",
        }
        if extra_vols:
            volumes = dict(**volumes, **extra_vols)
        self.container = ContainerRunner(
            "fluentbit",
            network=network,
            image="cr.fluentbit.io/fluent/fluent-bit:2.1.10",
            volumes=volumes,
            memory_limit="2g",
            rm=True,
            cmd=["-c", "/fluent-bit.yaml"]
        )
