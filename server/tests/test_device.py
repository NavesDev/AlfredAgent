import threading
import time
from collections.abc import Callable

import pytest

from config import Device
from infra.audio.device import HEADROOM_MB, RETRY_S, OnDemandGpu


class Models:
    def __init__(self, gpu_fails: bool = False) -> None:
        self.loaded: list[str] = []
        self.released: list[str] = []
        self.gpu_fails = gpu_fails
        self.gpu_attempts = 0

    def gpu(self) -> str:
        self.gpu_attempts += 1
        if self.gpu_fails:
            raise RuntimeError("CUDA out of memory")
        self.loaded.append("gpu")
        return "gpu"

    def cpu(self) -> str:
        self.loaded.append("cpu")
        return "cpu"

    def make(
        self, device: Device = "cuda", idle_s: float = 60, free_mb: int = 12000
    ) -> OnDemandGpu[str]:
        return OnDemandGpu(
            "test",
            device,
            idle_s,
            self.gpu,
            self.cpu,
            self.released.append,
            need_mb=1000,
            free_mb=lambda: free_mb,
        )


def wait_for(condition: Callable[[], bool]) -> None:
    deadline = time.monotonic() + 2
    while not condition():
        assert time.monotonic() < deadline
        time.sleep(0.01)


def test_loads_on_the_gpu_once_and_reuses_it() -> None:
    models = Models()
    device = models.make()

    assert device.run(lambda m: m) == "gpu"
    assert device.run(lambda m: m) == "gpu"
    assert models.loaded == ["gpu"]


def test_cpu_device_never_touches_the_gpu() -> None:
    models = Models()

    assert models.make("cpu").run(lambda m: m) == "cpu"
    assert models.loaded == ["cpu"]


def test_falls_back_to_cpu_when_the_gpu_cannot_load() -> None:
    models = Models(gpu_fails=True)

    assert models.make().run(lambda m: m) == "cpu"


def test_uses_the_cpu_when_the_gpu_lacks_headroom() -> None:
    models = Models()
    device = models.make(free_mb=1000 + HEADROOM_MB - 1)

    assert device.run(lambda m: m) == "cpu"
    assert models.gpu_attempts == 0 and device.wants_gpu  # checked again on the next call


def test_after_a_failed_load_stays_on_cpu_for_a_while(monkeypatch: pytest.MonkeyPatch) -> None:
    now = [1000.0]
    monkeypatch.setattr(time, "monotonic", lambda: now[0])
    models = Models(gpu_fails=True)
    device = models.make()

    device.run(lambda m: m)
    device.run(lambda m: m)
    assert models.gpu_attempts == 1 and not device.wants_gpu

    now[0] += RETRY_S
    models.gpu_fails = False
    assert device.wants_gpu
    assert device.run(lambda m: m) == "gpu"


def test_gpu_failure_during_a_call_releases_the_gpu_and_retries_on_cpu() -> None:
    models = Models()
    device = models.make()

    def task(model: str) -> str:
        if model == "gpu":
            raise RuntimeError("CUDA out of memory")
        return model

    assert device.run(task) == "cpu"
    assert models.released == ["gpu"] and not device.on_gpu
    assert device.run(lambda m: m) == "gpu"  # the next call tries the GPU again


def test_releases_the_gpu_after_idle() -> None:
    models = Models()
    device = models.make(idle_s=0.05)

    device.run(lambda m: m)

    wait_for(lambda: models.released == ["gpu"])
    assert not device.on_gpu


def test_use_resets_the_idle_timer() -> None:
    models = Models()
    device = models.make(idle_s=0.2)

    for _ in range(4):
        device.run(lambda m: m)
        time.sleep(0.1)

    assert models.released == []


def test_warm_loads_in_the_background() -> None:
    models = Models()
    loading = threading.Event()
    gpu = models.gpu
    models.gpu = lambda: (loading.wait(1), gpu())[1]  # type: ignore[method-assign]
    device = models.make()

    device.warm()
    assert models.loaded == []
    loading.set()

    wait_for(lambda: device.on_gpu)
    assert device.run(lambda m: m) == "gpu" and models.loaded == ["gpu"]
