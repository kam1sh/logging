import asyncio
import subprocess

import pytest

from o11y_tests.container import ContainerProfiler
from o11y_tests.vector import Vector
from o11y_tests.fluentbit import Fluentbit


@pytest.fixture
def lokiprof():
    return ContainerProfiler("grafana-loki-1")

@pytest.mark.fluentbit
@pytest.mark.asyncio
async def test_fluentbit(lokiprof):
    fluentbit = Fluentbit(
        network="grafana_loki",
        config_name="loki.yaml",
    )
    # start fluent-bit
    fluentbit.container.start()
    print("fluentbit started")
    fbprof = fluentbit.container.profiler()
    tasks = [fbprof.dispatch_task(), lokiprof.dispatch_task()]
    # wait for fluent-bit to finish
    try:
        await fluentbit.container.wait()
    finally:
        await fluentbit.container.kill()
        fbprof.stop()
        lokiprof.stop()
        await asyncio.wait(tasks)
        print("total:")
        print("Loki:      ", lokiprof.report())
        print("Fluent-bit:", fbprof.report())

@pytest.mark.vector
@pytest.mark.asyncio
async def test_vector(lokiprof):
    vector = Vector(
        network="grafana_loki",
        config_name="loki.yaml",
    )
    vector.container.start()
    print("vector started")
    vprof = vector.profiler()
    tasks = [vprof.dispatch_task(), lokiprof.dispatch_task()]
    try:
        await vector.wait(component="loki")
    finally:
        vprof.stop()
        lokiprof.stop()
        await asyncio.wait(tasks)
        print("total:")
        print("Loki:  ", lokiprof.report())
        print("Vector:", vprof.report())

def clear_pagecache():
    proc = subprocess.run(
        ["sudo", "tee", "/proc/sys/vm/drop_caches"],
        input="1",
        encoding="utf-8",
        stdout=subprocess.DEVNULL
    )
    proc.check_returncode()
