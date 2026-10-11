"""Named sessions Alfred delegates to: create, run one task at a time each, clear, delete.

Each session has its own queue and worker; results are spoken when a task ends (ADR 0007).
"""

import asyncio
import contextlib
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from errors import AgentError, SessionError, SessionNotFound, SessionProtected
from events import EventBus
from infra.claude.agents import KINDS, AgentKind
from infra.claude.alfred import Reply
from models.session import SessionView, Status

ACTIVITY_MAX = 80


class Session(Protocol):
    name: str
    kind: AgentKind
    model: str
    cwd: Path

    async def run(self, task: str) -> Reply: ...
    async def clear(self) -> None: ...


class Speaker(Protocol):
    def say(self, text: str) -> None: ...


# (kind, name, cwd) -> a session that connects on its first task
SessionFactory = Callable[[AgentKind, str, Path], Session]


@dataclass
class Slot:
    session: Session
    protected: bool
    queue: asyncio.Queue[str] = field(default_factory=asyncio.Queue)
    worker: asyncio.Task[None] | None = None
    status: Status = "idle"
    task: str | None = None
    activity: str | None = None
    tasks_done: int = 0
    tokens: int = 0
    last_summary: str | None = None


class Sessions:
    def __init__(
        self,
        bus: EventBus,
        talker: Speaker,
        factory: SessionFactory,
        max_active: int,
        home: Path,
    ) -> None:
        self._bus, self._talker, self._factory = bus, talker, factory
        self._max_active, self._home = max_active, home
        self._slots: dict[str, Slot] = {}

    def add(self, session: Session, protected: bool = False) -> SessionView:
        """Registers a built session and starts its worker (used at boot for "sistema")."""
        slot = Slot(session, protected)
        self._slots[session.name.lower()] = slot
        slot.worker = asyncio.create_task(self._work(slot))
        view = self._view(slot)
        self._bus.publish("session_created", session=view.model_dump())
        return view

    def create(self, kind: str, name: str, cwd: str | None = None) -> SessionView:
        name = name.strip()
        if kind not in KINDS:
            raise SessionError(f"Não conheço o tipo {kind}. Tipos: {', '.join(KINDS)}.")
        if not name:
            raise SessionError("A sessão precisa de um nome.")
        if name.lower() in self._slots:
            raise SessionError(f"Já existe uma sessão chamada {name}.")
        if len(self._slots) >= self._max_active:
            raise SessionError(
                f"Já tenho {self._max_active} sessões, o limite. Apague uma antes de criar outra."
            )
        path = Path(cwd).expanduser() if cwd else self._home
        if not path.is_dir():
            raise SessionError(f"A pasta {cwd} não existe.")
        return self.add(self._factory(KINDS[kind], name, path))

    def delegate(self, name: str, task: str) -> str:
        """Returns right away with what Alfred tells the user; the worker runs the task."""
        slot = self._get(name)
        ahead = slot.queue.qsize() + (slot.status == "busy")
        slot.queue.put_nowait(task)
        self._publish_status(slot)
        name = slot.session.name
        if ahead:
            return f"A sessão {name} está ocupada; a tarefa entrou na fila (posição {ahead})."
        return f"Tarefa enviada para a sessão {name}. Ela avisa por voz quando terminar."

    async def clear(self, name: str) -> SessionView:
        """Cancels the running task, drops the queue and forgets the conversation."""
        slot = self._get(name)
        await self._stop(slot)
        slot.status, slot.task, slot.activity = "idle", None, None
        slot.tasks_done, slot.tokens, slot.last_summary = 0, 0, None
        slot.worker = asyncio.create_task(self._work(slot))
        view = self._view(slot)
        self._bus.publish("session_cleared", session=view.model_dump())
        return view

    async def delete(self, name: str) -> None:
        slot = self._get(name)
        if slot.protected:
            raise SessionProtected(f"A sessão {slot.session.name} não pode ser apagada, só limpa.")
        await self._stop(slot)
        del self._slots[slot.session.name.lower()]
        self._bus.publish("session_deleted", name=slot.session.name)

    def list(self) -> list[SessionView]:
        return [self._view(slot) for slot in self._slots.values()]

    async def run(self) -> None:
        """Keeps each busy session's last activity from the agents' progress events."""
        queue = self._bus.subscribe()
        try:
            while True:
                event = await queue.get()
                if event["type"] != "agent_progress":
                    continue
                slot = self._slots.get(str(event.get("session", "")).lower())
                if slot is None or slot.status != "busy":
                    continue
                text = " ".join(str(event.get("label") or event.get("content") or "").split())
                slot.activity = text[:ACTIVITY_MAX] or None
                self._publish_status(slot)
        finally:
            self._bus.unsubscribe(queue)

    async def _work(self, slot: Slot) -> None:
        while True:
            await self._process(slot, await slot.queue.get())

    async def _process(self, slot: Slot, task: str) -> None:
        name = slot.session.name
        slot.status, slot.task, slot.activity = "busy", task, None
        self._publish_status(slot)
        try:
            reply = await slot.session.run(task)
        except AgentError as e:
            slot.status = "error"
            self._bus.publish("error", where=name, message=str(e))
            self._talker.say(f"A sessão {name} não conseguiu terminar a tarefa.")
        else:
            slot.status = "idle"
            slot.tasks_done += 1
            slot.tokens += reply.tokens
            slot.last_summary = reply.summary or None
            self._talker.say(reply.summary or f"A sessão {name} terminou.")
        slot.task, slot.activity = None, None
        self._publish_status(slot)

    async def _stop(self, slot: Slot) -> None:
        if slot.worker is not None:
            slot.worker.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await slot.worker
        while not slot.queue.empty():
            slot.queue.get_nowait()
        await slot.session.clear()

    def _get(self, name: str) -> Slot:
        slot = self._slots.get(name.strip().lower())
        if slot is None:
            raise SessionNotFound(f"Não existe sessão chamada {name}.")
        return slot

    def _publish_status(self, slot: Slot) -> None:
        self._bus.publish("session_status", session=self._view(slot).model_dump())

    def _view(self, slot: Slot) -> SessionView:
        s = slot.session
        return SessionView(
            name=s.name,
            kind=s.kind.kind,
            label=s.kind.label,
            model=s.model,
            cwd=_short(s.cwd, self._home),
            status=slot.status,
            task=slot.task,
            activity=slot.activity,
            queue=slot.queue.qsize(),
            tasks_done=slot.tasks_done,
            tokens=slot.tokens,
            last_summary=slot.last_summary,
            protected=slot.protected,
        )


def _short(path: Path, home: Path) -> str:
    try:
        rest = path.relative_to(home)
    except ValueError:
        return str(path)
    return "~" if rest == Path() else f"~/{rest}"
