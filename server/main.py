"""Alfred server: voice loop + main agent + /ws, in one asyncio process."""

import asyncio
import logging
import sys
import threading
from pathlib import Path

import uvicorn

from api.app import create_app
from config import Config, load_config
from controllers.router import Router
from errors import ConfigError, DependencyError
from events import EventBus
from infra.audio import check_audio
from infra.audio.listener import Listener, OpenWakeWord, load_vad, load_whisper
from infra.audio.talker import Talker, load_kokoro, open_speaker
from infra.claude.alfred import AlfredAgent, check_cli
from infra.claude.state import DailyState

log = logging.getLogger("alfred")


async def serve(config: Config) -> None:
    check_cli()
    check_audio(config.listener.sample_rate)
    loop = asyncio.get_running_loop()
    bus = EventBus(loop)

    log.info("loading models…")
    talker = Talker(bus, load_kokoro(config.kokoro), open_speaker())
    agent = AlfredAgent(
        bus,
        DailyState(config.storage.state_path),
        model=config.agents.default_model,
        timeout_s=config.agents.timeout_s,
    )
    await agent.start()
    router = Router(bus, agent, talker)
    listener = Listener(
        bus,
        config.listener,
        config.wakeword.threshold,
        wake=OpenWakeWord(config.wakeword.model),
        is_speech=load_vad(),
        transcribe=load_whisper(config.whisper),
        on_transcript=lambda text: asyncio.run_coroutine_threadsafe(
            router.handle(text), loop
        ).result(),
        muted=lambda: talker.is_speaking,
    )

    stop = threading.Event()
    for worker in (listener.run, talker.run):
        threading.Thread(target=worker, args=(stop,), daemon=True).start()

    app = create_app()
    app.state.bus = bus
    server = uvicorn.Server(
        uvicorn.Config(app, config.api.host, config.api.port, log_level="warning")
    )
    log.info(
        "ready on ws://%s:%d/ws, say %r", config.api.host, config.api.port, config.wakeword.model
    )
    try:
        await server.serve()
    finally:
        stop.set()


def main(config_path: Path = Path("config.yaml")) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    try:
        asyncio.run(serve(load_config(config_path)))
    except (ConfigError, DependencyError) as e:
        print(f"alfred: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
