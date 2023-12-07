import asyncio
from pathlib import Path
import subprocess

import pytest
import random

from o11y_tests.container import ContainerProfiler, ContainerRunner, volume_path
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search, A


@pytest.fixture
def client():
    cert_path = volume_path("es_certs")
    ca = cert_path / "ca" / "ca.crt"
    client = Elasticsearch(
        "https://localhost:9200",
        ca_certs=str(ca),
        basic_auth=("elastic", "changeme")
    )
    resp = client.indices.get(index="logstash-*")
    idx = list(resp.body.keys())[0]
    return Search(using=client, index=idx)

@pytest.mark.fluentbit
@pytest.mark.elastic
@pytest.mark.asyncio
async def test_fluentbit():
    fluentbit = ContainerRunner.fluentbit(
        network="elastic",
        config_name="elastic.yaml",
        extra_vols={"es_certs": "/ca"}
    )
    # start fluent-bit
    fluentbit.start()
    print("fluentbit started")
    # setup profiling
    esprof = ContainerProfiler("es-es01-1")
    fbprof = fluentbit.profiler()
    tasks = [fbprof.dispatch_task(), esprof.dispatch_task()]
    # wait for fluent-bit to finish
    try:
        await fluentbit.wait()
    finally:
        await fluentbit.kill()
        fbprof.stop()
        esprof.stop()
        await asyncio.wait(tasks)
        print("total:")
        print("Elasticsearch:", esprof.report())
        print("Fluent-bit:   ", fbprof.report())

@pytest.mark.parametrize("pagecache", [True, False], ids=["with pagecache", "without cache"])
def test_simple_query(benchmark, pagecache, client):
    client.query("match", service="feeder")
    def randsearch():
        nonlocal client
        offset = random.randrange(1, 5000)
        limit = random.randrange(5001, 10000)
        client = client[offset:limit]
        client.execute()
    if pagecache:
        benchmark(randsearch)
    else:
        benchmark.pedantic(randsearch, setup=clear_pagecache, rounds=50)


@pytest.mark.parametrize("pagecache", [True, False], ids=["with pagecache", "without cache"])
def test_group_query(benchmark, pagecache, client):
    client.aggs.metric("count_by_svc", "value_count", field="service.keyword")
    def randsearch():
        nonlocal client
        resp = client.execute()
        assert resp
    if pagecache:
        benchmark(randsearch)
    else:
        benchmark.pedantic(randsearch, setup=clear_pagecache, rounds=50)

def clear_pagecache():
    proc = subprocess.run(
        ["sudo", "tee", "/proc/sys/vm/drop_caches"],
        input="1",
        encoding="utf-8",
        stdout=subprocess.DEVNULL
    )
    proc.check_returncode()
