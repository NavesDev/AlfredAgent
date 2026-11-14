"""Keep a model on the GPU only while it is in use, falling back to the CPU.

The GPU is shared with the image service, whose jobs take up to ~11 GB of the 12 GB. The
model loads on the GPU on demand, only when no other process runs a big job there and
`HEADROOM_MB` stays free, and is released after `idle_s` without use. A busy GPU
or any GPU failure (no CUDA, out of memory) runs that call on the CPU, so voice never
blocks. After a failed load it stays on the CPU for `RETRY_S`: a failed load costs ~2.5 s.
See ADR 0010.
"""

import gc
import logging
import os
import subprocess
import threading
import time
from collections.abc import Callable
from typing import Generic, Literal, TypeVar

M = TypeVar("M")
R = TypeVar("R")

RETRY_S = 60
HEADROOM_MB = 2048
OTHER_JOB_MB = 1024

log = logging.getLogger(__name__)


def _smi(query: str) -> list[list[int]]:
    out = subprocess.run(
        ["nvidia-smi", f"--query-{query}", "--format=csv,noheader,nounits"],
        capture_output=True,
        text=True,
        timeout=5,
        check=True,
    ).stdout
    return [[int(v) for v in line.split(",")] for line in out.splitlines() if line.strip()]


def gpu_room_mb() -> int:
    """GPU memory voice may take: the free memory, or 0 while another process runs a big
    job (the image service), which grows to its peak after we'd load. Uses nvidia-smi
    (~25 ms) rather than torch, which would open a CUDA context (~300 MB) just to ask."""
    try:
        others = [mb for pid, mb in _smi("compute-apps=pid,used_memory") if pid != os.getpid()]
        if any(mb >= OTHER_JOB_MB for mb in others):
            return 0
        return _smi("gpu=memory.free")[0][0]
    except Exception:
        return 0


class OnDemandGpu(Generic[M]):
    def __init__(
        self,
        name: str,
        device: Literal["cpu", "cuda"],
        idle_s: float,
        load_gpu: Callable[[], M],
        load_cpu: Callable[[], M],
        release: Callable[[M], None] = lambda _: None,
        need_mb: int = 0,
        free_mb: Callable[[], int] = gpu_room_mb,
    ) -> None:
        self._name, self._device, self._idle_s = name, device, idle_s
        self._need_mb, self._free_mb = need_mb, free_mb
        self._load_gpu, self._load_cpu, self._release = load_gpu, load_cpu, release
        self._lock = threading.RLock()
        self._gpu: M | None = None
        self._cpu: M | None = None
        self._timer: threading.Timer | None = None
        self._failed_at: float = -RETRY_S

    @property
    def on_gpu(self) -> bool:
        return self._gpu is not None

    @property
    def wants_gpu(self) -> bool:
        """Runs on the GPU, or will on the next call (no recent failure)."""
        return self._device == "cuda" and time.monotonic() - self._failed_at >= RETRY_S

    def warm(self) -> None:
        """Start loading on the GPU in the background, ahead of the next `run`."""
        if self.wants_gpu and self._gpu is None:
            threading.Thread(target=self.run, args=(lambda _: None,), daemon=True).start()

    def run(self, task: Callable[[M], R]) -> R:
        with self._lock:
            self._cancel_timer()
            try:
                gpu = self._gpu_model()
                if gpu is not None:
                    try:
                        return task(gpu)
                    except Exception:
                        log.warning("%s failed on the GPU, using CPU", self._name, exc_info=True)
                        self._drop()
                if self._cpu is None:
                    self._cpu = self._load_cpu()
                return task(self._cpu)
            finally:
                self._schedule_drop()

    def _gpu_model(self) -> M | None:
        if self._gpu is None and self.wants_gpu:
            free = self._free_mb()
            if free < self._need_mb + HEADROOM_MB:
                log.info("GPU busy (%d MB for voice), %s runs on the CPU", free, self._name)
                return None
            try:
                self._gpu = self._load_gpu()
            except Exception as e:
                log.warning("cannot load %s on the GPU, using the CPU: %s", self._name, e)
                self._failed_at = time.monotonic()
                self._drop()
        return self._gpu

    def _drop(self) -> None:
        gpu, self._gpu = self._gpu, None
        if gpu is not None:
            self._release(gpu)
        del gpu
        gc.collect()

    def _cancel_timer(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    def _schedule_drop(self) -> None:
        if self._gpu is None:
            return
        timer = threading.Timer(self._idle_s, lambda: self._expire(timer))
        timer.daemon = True
        self._timer = timer
        timer.start()

    def _expire(self, timer: threading.Timer) -> None:
        with self._lock:
            if self._timer is timer:
                self._timer = None
                self._drop()
                log.info("%s released the GPU after %.0f s idle", self._name, self._idle_s)
