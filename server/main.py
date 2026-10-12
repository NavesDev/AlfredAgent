"""Alfred server: voice loop + main agent + /ws, in one asyncio process."""

import asyncio
import logging
import sys
import threading
from collections.abc import Callable
from pathlib import Path

import uvicorn

from api.app import create_app
from config import Config, load_config
from controllers.projects import Projects
from controllers.router import Router
from controllers.sessions import Sessions
from controllers.settings import Settings
from errors import ConfigError, DependencyError
from events import EventBus
from infra.audio import check_audio
from infra.audio.listener import Listener, OpenWakeWord, load_vad, load_whisper
from infra.audio.talker import Talker, load_kokoro, open_speaker
from infra.claude.agents import AgentKind, SessionContext
from infra.claude.alfred import AlfredAgent, check_cli
from infra.claude.session import CodingSession
from infra.claude.state import DailyState
from infra.claude.tools import session_tools
from models import settings as settings_model
from models.db import open_db

log = logging.getLogger("alfred")


async def serve(config: Config) -> None:
    check_cli()
    check_audio(config.listener.sample_rate)
    loop = asyncio.get_running_loop()
    bus = EventBus(loop)

    log.info("loading models…")
    talker = Talker(
        bus,
        load_kokoro(config.kokoro),
        open_speaker(),
        acknowledgements=config.kokoro.acknowledgements,
    )

    db = open_db(config.storage.db_path)
    settings_model.seed(db, config.seed_defaults())
    settings = Settings(db, bus)

    def new_session(kind: AgentKind, context: Callable[[], SessionContext]) -> CodingSession:
        return CodingSession(bus, kind, context, timeout_s=config.agents.session_timeout_s)

    sessions = Sessions(bus, talker, db, settings, new_session, home=Path.home())
    sessions.load()
    projects = Projects(db, bus)
    agent = AlfredAgent(
        bus,
        DailyState(config.storage.state_path),
        model=lambda: settings.resolve("alfred", None, None),
        timeout_s=config.agents.timeout_s,
        tools=session_tools(sessions, projects),
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
        chime=talker.chime,
        acknowledge=talker.acknowledge,
    )

    jobs = [asyncio.create_task(job()) for job in (sessions.run, sessions.watch_idle, settings.run)]
    stop = threading.Event()
    for worker in (listener.run, talker.run):
        threading.Thread(target=worker, args=(stop,), daemon=True).start()

    app = create_app()
    app.state.bus = bus
    app.state.alfred = agent
    app.state.sessions = sessions
    app.state.projects = projects
    app.state.settings = settings
    server = uvicorn.Server(
        uvicorn.Config(app, config.api.host, config.api.port, log_level="warning")
    )
    log.info(
        "ready on ws://%s:%d/ws, say %r", config.api.host, config.api.port, config.wakeword.name
    )
    try:
        await server.serve()
    finally:
        stop.set()
        for job in jobs:
            job.cancel()


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
