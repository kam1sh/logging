import asyncio
from pathlib import Path

from gql import gql, Client
from gql.transport.websockets import WebsocketsTransport

from o11y_tests.container import ContainerRunner, ContainerProfiler

class Vector:
    def __init__(self, network, config_name, extra_vols=None) -> None:
        project_root = Path().resolve().parents[0]
        pth = project_root / "logging" / "vector"
        volumes = {
            str(project_root / "logs"): "/logs",
            str(pth / config_name): "/etc/vector/vector.yaml",
        }
        if extra_vols:
            volumes = dict(**volumes, **extra_vols)
        self.container = ContainerRunner(
            "vector",
            network,
            image="docker.io/timberio/vector:0.34.1-alpine",
            volumes=volumes,
            memory_limit="1g",
            rm=True,
            args=["-p", "127.0.0.1:8686:8686"]
        )
        url = "ws://127.0.0.1:8686/graphql"
        transport = WebsocketsTransport(url, ssl=False)
        self.client = Client(transport=transport)
        self.stop_event = asyncio.Event()
    

    async def wait(self, component):
        async for num in self.throughput_events(component=component):
            if num == 0:
                await self.container.kill()
                return

    def profiler(self):
        return self.container.profiler()

    async def throughput_events(self, component):
        query = gql("""
subscription componentReceivedEventsThroughputs {
  componentReceivedEventsThroughputs {
    componentId
    throughput
  }
}
""")
        async for result in self.client.subscribe_async(query):
            if self.stop_event.is_set():
                return
            items = result["componentReceivedEventsThroughputs"]
            for it in items:
                if it["componentId"] == component:
                    yield it["throughput"]
