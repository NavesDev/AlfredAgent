import asyncio
import threading

from events import EventBus


async def test_subscriber_receives_published_event_with_type_and_timestamp() -> None:
    bus = EventBus(asyncio.get_running_loop())
    queue = bus.subscribe()

    bus.publish("voice_state", state="listening")

    event = await asyncio.wait_for(queue.get(), 1)
    assert event["type"] == "voice_state"
    assert event["state"] == "listening"
    assert isinstance(event["ts"], float)


async def test_publish_from_another_thread_reaches_subscriber() -> None:
    bus = EventBus(asyncio.get_running_loop())
    queue = bus.subscribe()

    threading.Thread(target=bus.publish, args=("transcript",), kwargs={"text": "oi"}).start()

    event = await asyncio.wait_for(queue.get(), 1)
    assert event["text"] == "oi"


async def test_unsubscribed_queue_stops_receiving() -> None:
    bus = EventBus(asyncio.get_running_loop())
    queue = bus.subscribe()
    bus.unsubscribe(queue)

    bus.publish("voice_state", state="idle")
    await asyncio.sleep(0.01)

    assert queue.empty()
