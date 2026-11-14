import asyncio
from pathlib import Path

from claude_agent_sdk import RateLimitEvent, RateLimitInfo

from controllers.usage import Usage
from events import EventBus
from tests.conftest import drain
from tests.test_alfred import FakeConnect, result
from tests.test_session import session
from tests.test_sessions import Env, settle


def limit(window: str, status: str = "allowed", **info: float | int | None) -> RateLimitEvent:
    return RateLimitEvent(
        rate_limit_info=RateLimitInfo(status=status, rate_limit_type=window, **info),  # type: ignore[arg-type]
        uuid="u",
        session_id="s1",
    )


async def test_a_session_run_reports_limits_and_how_full_its_context_is(bus: EventBus) -> None:
    queue = bus.subscribe()
    connect = FakeConnect([limit("five_hour", utilization=0.72, resets_at=100), result("ok")])

    reply = await session(bus, connect).run("a")
    await asyncio.sleep(0)  # the bus fans out on the next loop turn

    [event] = [e for e in drain(queue) if e["type"] == "rate_limit"]
    assert (event["window"], event["status"], event["utilization"]) == (
        "five_hour",
        "allowed",
        0.72,
    )
    assert reply.context == (41_000, 200_000)


async def test_usage_keeps_the_latest_report_per_window(bus: EventBus, tmp_path: Path) -> None:
    env = Env(bus, tmp_path)
    clock = iter([10.0, 20.0, 30.0])
    usage = Usage(bus, env.sessions, env.settings, clock=lambda: next(clock))
    task = asyncio.create_task(usage.run())
    await settle()

    bus.publish("rate_limit", window="five_hour", status="allowed", utilization=0.5, resets_at=99)
    bus.publish("rate_limit", window="seven_day", status="allowed", utilization=0.1, resets_at=None)
    bus.publish("rate_limit", window="five_hour", status="allowed_warning", utilization=None)
    await settle()
    task.cancel()

    view = usage.view()
    five = next(lim for lim in view.limits if lim.window == "five_hour")
    assert (five.status, five.utilization, five.resets_at, five.read_at) == (
        "allowed_warning",
        0.5,  # the warning left the share out: the last known one stays
        99,
        30.0,
    )
    assert len(view.limits) == 2
    assert view.max_active_sessions == 3
    assert view.open_sessions == 0
    assert [(s.name, s.tokens, s.context_max) for s in view.sessions] == [("sistema", 0, None)]
