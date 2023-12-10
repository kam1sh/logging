import asyncio
import subprocess
import statistics
from pathlib import Path

import psutil
import jc


CONTAINER_EXEC = "podman"


def volume_path(name):
    pth = subprocess.check_output([
        CONTAINER_EXEC, "volume", "inspect", "--format", "{{ .Mountpoint }}", name,
    ], encoding="utf-8").strip()
    return Path(pth)


class ContainerProfiler:
    executable = CONTAINER_EXEC

    def __init__(self, name: str) -> None:
        self.name = name
        ppid = subprocess.check_output(
            [self.executable, "inspect", "-f", "{{.State.Pid}}", name], encoding="utf8"
        ).strip()
        self.proc = psutil.Process(int(ppid))
        self.stop_event = asyncio.Event()
        self.cpu_over_time = []
        self.mem_over_time = []

    async def update_metrics(self):
        pids = [self.proc.pid] + [x.pid for x in self.proc.children(recursive=True)]
        cmd = await asyncio.subprocess.create_subprocess_exec(
            "pidstat",
            "-h",
            "-H",
            "-r",
            "-u",
            "-p",
            ",".join(map(str, pids)),
            "1",
            "1",
            stdout=subprocess.PIPE,
        )
        stdout = []
        async for line in cmd.stdout:
            stdout.append(line.decode())
        cpus, mems = [], []
        for proc in jc.parse("pidstat_s", stdout):
            cpus.append(proc["percent_cpu"])
            mems.append(proc["rss"])
        self.cpu_over_time.append(sum(cpus))
        self.mem_over_time.append(sum(mems))

    def dispatch_task(self):
        return asyncio.create_task(self.loop())

    async def loop(self):
        while not self.stop_event.is_set():
            try:
                await self.update_metrics()
                # print(f"{self.name} current cpu: {self.cpu_over_time[-1]:.1f}%")
                # print(
                #     f"{self.name} current memory: {self.mem_over_time[-1] / 1024:.1f} MB"
                # )
            except psutil.NoSuchProcess:
                print(f"Container {self.name} finished")
                return

    def stop(self):
        self.stop_event.set()

    @property
    def memory_stats(self):
        return dict(
            avg=statistics.fmean(self.mem_over_time) / 1024,
            max=max(self.mem_over_time) / 1024,
        )

    @property
    def cpu_stats(self):
        return dict(
            avg=statistics.fmean(self.cpu_over_time), max=max(self.cpu_over_time)
        )

    def report(self) -> str:
        cpu = self.cpu_stats
        mem = self.memory_stats
        return "cpu: avg={:.1f}%, max={:.1f}%; mem: avg={:.1f}MB, max={:.1f}MB".format(
            cpu["avg"], cpu["max"], mem["avg"], mem["max"]
        )

    def __repr__(self) -> str:
        return "{}({!r})".format(self.__class__.__name__, self.name)


class ContainerRunner:
    def __init__(
        self,
        name,
        network,
        image,
        volumes: dict[str, str],
        memory_limit=None,
        rm=False,
        cmd=None,
        args=None,
    ) -> None:
        self.name = name
        self.network = network
        self.image = image
        self.volumes = volumes
        self.memlimit = memory_limit
        self.delete = rm
        self.cmdline = self.build_cmdline(args=args, cmd=cmd)
        self.cid = None

    def build_cmdline(self, args=None, cmd=None):
        cmdline = [
            CONTAINER_EXEC,
            "run",
            "--network",
            self.network,
            "-d",
            "--name",
            self.name,
            "-m",
            "2g",
        ]
        if self.memlimit:
            cmdline.extend(["-m", self.memlimit])
        if self.delete:
            cmdline.append("--rm")
        if args:
            cmdline.extend(args)
        cmdline.extend(
            it
            for arr in [["-v", f"{k}:{v}"] for k, v in self.volumes.items()]
            for it in arr
        )
        cmdline.append(self.image)
        if cmd:
            cmdline.extend(cmd)
        return cmdline

    def start(self):
        self.cid = subprocess.check_output(self.cmdline, encoding="utf8")
        assert self.cid

    async def wait(self):
        proc = await asyncio.subprocess.create_subprocess_exec(
            CONTAINER_EXEC, "wait", self.name, stdout=asyncio.subprocess.DEVNULL
        )
        return await proc.wait()

    def profiler(self):
        return ContainerProfiler(self.name)

    async def kill(self):
        proc = await asyncio.subprocess.create_subprocess_exec(
            CONTAINER_EXEC, "kill", "--signal", "KILL", self.name,
            stderr=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.DEVNULL
        )
        await proc.wait()
