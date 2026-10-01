import asyncio

import pytest

from events import Event, EventBus


@pytest.fixture
async def bus() -> EventBus:
    return EventBus(asyncio.get_running_loop())


def drain(queue: asyncio.Queue[Event]) -> list[Event]:
    return [queue.get_nowait() for _ in range(queue.qsize())]
