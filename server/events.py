"""In-memory pub/sub. publish() is safe from any thread; subscribers are asyncio queues."""

import asyncio
import time
from typing import Any

Event = dict[str, Any]


class EventBus:
    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        self._queues: set[asyncio.Queue[Event]] = set()

    def subscribe(self) -> asyncio.Queue[Event]:
        queue: asyncio.Queue[Event] = asyncio.Queue()
        self._queues.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[Event]) -> None:
        self._queues.discard(queue)

    def publish(self, type: str, **data: Any) -> None:
        event = {"type": type, "ts": time.time(), **data}
        self._loop.call_soon_threadsafe(self._fan_out, event)

    def _fan_out(self, event: Event) -> None:
        for queue in self._queues:
            queue.put_nowait(event)
