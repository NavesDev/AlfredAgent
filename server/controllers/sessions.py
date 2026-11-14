"""Named sessions Alfred delegates to: create, run one task at a time each, clear, delete.

Sessions are stored in SQLite and resume their conversation after a restart. Each has its own
queue and worker. A worker needs one of max_active_sessions slots (open claude processes) to run;
idle sessions give theirs up after idle_minutes, or sooner when another session needs it.
"""

import asyncio
import builtins
import contextlib
import logging
import sqlite3
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from controllers.settings import EFFORTS, Settings
from errors import AgentError, SessionError, SessionNotFound, SessionProtected
from events import EventBus
from infra.claude.agents import DEFAULT_SESSION, KINDS, AgentKind, SessionContext
from infra.claude.alfred import Reply
from models import project
from models import session as records
from models.session import Phase, SessionView, Status, SubagentView

ACTIVITY_MAX = 80
IDLE_CHECK_S = 30

log = logging.getLogger("alfred.sessions")


class Session(Protocol):
    name: str
    kind: AgentKind

    @property
    def connected(self) -> bool: ...

    async def run(self, task: str) -> Reply: ...
    async def disconnect(self) -> None: ...


class Speaker(Protocol):
    def notify(self, text: str) -> None: ...


# (kind, context read on every connect) -> a session that connects on its first task
SessionFactory = Callable[[AgentKind, Callable[[], SessionContext]], Session]


@dataclass
class Slot:
    session: Session
    protected: bool
    queue: asyncio.Queue[str] = field(default_factory=asyncio.Queue)
    worker: asyncio.Task[None] | None = None
    status: Status = "idle"
    phase: Phase | None = None
    task: str | None = None
    activity: str | None = None
    waiting: bool = False
    tasks_done: int = 0
    tokens: int = 0
    last_summary: str | None = None
    last_error: str | None = None
    context: tuple[int, int] | None = None
    last_used: float = 0.0
    subagents: dict[str, SubagentView] = field(default_factory=dict)


class Sessions:
    def __init__(
        self,
        bus: EventBus,
        talker: Speaker,
        db: sqlite3.Connection,
        settings: Settings,
        factory: SessionFactory,
        home: Path,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._bus, self._talker, self._db = bus, talker, db
        self._settings, self._factory, self._home, self._clock = settings, factory, home, clock
        self._slots: dict[str, Slot] = {}
        self._waiters: list[asyncio.Future[None]] = []

    def load(self) -> None:
        """Boot: seeds "sistema" and registers every stored session, all disconnected."""
        if records.get_session(self._db, DEFAULT_SESSION) is None:
            records.insert_session(self._db, DEFAULT_SESSION, "geral", protected=True)
        for record in records.list_sessions(self._db):
            self._register(record)

    def create(
        self,
        kind: str,
        name: str,
        workspace_id: int | None = None,
        model: str | None = None,
        effort: str | None = None,
        aliases: list[str] | None = None,
    ) -> SessionView:
        name = name.strip()
        if kind not in KINDS:
            raise SessionError(f"Não conheço o tipo {kind}. Tipos: {', '.join(KINDS)}.")
        if not name:
            raise SessionError("A sessão precisa de um nome.")
        if (owner := self._owner(name)) is not None:
            raise SessionError(f"Já existe uma sessão chamada {name}: {owner}.")
        aliases = self._check_aliases(name, aliases or [])
        if workspace_id is None and KINDS[kind].needs_workspace:
            raise SessionError(f"Uma sessão de {KINDS[kind].label} precisa de um workspace.")
        if workspace_id is not None and project.get_workspace(self._db, workspace_id) is None:
            raise SessionError("Esse workspace não existe.")
        _check_effort(effort)
        record = records.insert_session(
            self._db, name, kind, workspace_id, model or None, effort or None, aliases=aliases
        )
        return self._register(record)

    def set_aliases(self, name: str, aliases: list[str]) -> SessionView:
        """Replaces the spoken alternatives for a session's name."""
        slot = self._get(name)
        clean = self._check_aliases(slot.session.name, aliases)
        records.update_session(self._db, slot.session.name, aliases=clean)
        self._publish_status(slot)
        return self._view(slot)

    def update(self, name: str, model: str | None = None, effort: str | None = None) -> SessionView:
        """Overrides the kind's model or effort; an empty string goes back to the kind's."""
        slot = self._get(name)
        _check_effort(effort or None)
        changes = {k: v or None for k, v in (("model", model), ("effort", effort)) if v is not None}
        records.update_session(self._db, slot.session.name, **changes)
        self._publish_status(slot)
        return self._view(slot)

    def delegate(self, name: str, task: str) -> str:
        """Returns right away with what Alfred tells the user; the worker runs the task."""
        slot = self._get(name)
        ahead = slot.queue.qsize() + (slot.status == "busy")
        slot.queue.put_nowait(task)
        self._publish_status(slot)
        name = slot.session.name
        if ahead:
            return f"A sessão {name} está ocupada; a tarefa entrou na fila (posição {ahead})."
        if not self._can_start(slot):
            return f"Todas as vagas estão ocupadas; a tarefa da sessão {name} entrou na fila."
        return f"Tarefa enviada para a sessão {name}. Ela avisa por voz quando terminar."

    async def clear(self, name: str) -> SessionView:
        """Cancels the running task, drops the queue and forgets the conversation."""
        slot = self._get(name)
        await self._stop(slot)
        records.update_session(self._db, slot.session.name, claude_session_id=None)
        slot.status, slot.task, slot.activity, slot.phase = "idle", None, None, None
        slot.tasks_done, slot.tokens, slot.last_summary, slot.last_error = 0, 0, None, None
        slot.context = None
        slot.subagents.clear()
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
        records.delete_session(self._db, slot.session.name)
        self._bus.publish("session_deleted", name=slot.session.name)

    def list(self) -> list[SessionView]:
        return [self._view(slot) for slot in self._slots.values()]

    async def run(self) -> None:
        """Keeps each busy session's activity, phase and subagents from the bus."""
        queue = self._bus.subscribe()
        try:
            while True:
                event = await queue.get()
                slot = self._slots.get(str(event.get("session", "")).lower())
                if slot is None or slot.status != "busy":
                    continue
                if self._apply(slot, event):
                    self._publish_status(slot)
        finally:
            self._bus.unsubscribe(queue)

    async def watch_idle(self) -> None:
        while True:
            await asyncio.sleep(IDLE_CHECK_S)
            await self.reap_idle()

    async def reap_idle(self) -> None:
        """Disconnects sessions idle for longer than idle_minutes; they resume on the next task."""
        limit = self._settings.app().idle_minutes * 60
        for slot in list(self._slots.values()):
            idle = slot.session.connected and slot.status != "busy"
            if idle and self._clock() - slot.last_used > limit:
                await slot.session.disconnect()
                self._publish_status(slot)
                self._wake()

    # --- internals ---------------------------------------------------------------------------

    def _register(self, record: records.SessionRecord) -> SessionView:
        name = record.name
        session = self._factory(KINDS[record.kind], lambda: self._context(name))
        slot = Slot(session, record.protected)
        self._slots[name.lower()] = slot
        slot.worker = asyncio.create_task(self._work(slot))
        view = self._view(slot)
        self._bus.publish("session_created", session=view.model_dump())
        return view

    def _context(self, name: str) -> SessionContext:
        record = records.get_session(self._db, name)
        assert record is not None, name
        ws, proj = self._place(record)
        model, effort = self._settings.resolve(record.kind, record.model, record.effort)
        return SessionContext(
            name=record.name,
            cwd=Path(ws.path) if ws else self._home,
            model=model,
            effort=effort,
            resume=record.claude_session_id,
            project=proj.name if proj else None,
            workspace=ws.name if ws else None,
            mcp_disabled=tuple(self._settings.app().mcp_disabled),
        )

    def _place(
        self, record: records.SessionRecord
    ) -> tuple[project.Workspace | None, project.Project | None]:
        ws = project.get_workspace(self._db, record.workspace_id) if record.workspace_id else None
        return ws, project.get_project(self._db, ws.project_id) if ws else None

    async def _work(self, slot: Slot) -> None:
        while True:
            task = await slot.queue.get()
            slot.task = task  # visible while it waits for a slot, not only once it runs
            await self._acquire(slot)
            await self._process(slot, task)
            self._wake()

    def _can_start(self, slot: Slot) -> bool:
        if slot.session.connected:
            return True
        connected = [s for s in self._slots.values() if s.session.connected]
        if len(connected) < self._settings.app().max_active_sessions:
            return True
        return any(s.status != "busy" for s in connected)

    async def _acquire(self, slot: Slot) -> None:
        """Waits for a free slot, evicting the longest-idle connected session if needed."""
        while True:
            if slot.session.connected:
                break
            connected = [s for s in self._slots.values() if s.session.connected]
            if len(connected) < self._settings.app().max_active_sessions:
                break
            idle = [s for s in connected if s.status != "busy" and s.queue.empty()]
            if idle:
                oldest = min(idle, key=lambda s: s.last_used)
                await oldest.session.disconnect()
                self._publish_status(oldest)
                break
            slot.waiting = True
            self._publish_status(slot)
            waiter = asyncio.get_running_loop().create_future()
            self._waiters.append(waiter)
            try:
                await waiter
            finally:
                slot.waiting = False
                if waiter in self._waiters:
                    self._waiters.remove(waiter)

    def _wake(self) -> None:
        """A slot may be free: let the waiting workers try again, in order."""
        waiters, self._waiters = self._waiters, []
        for waiter in waiters:
            if not waiter.done():
                waiter.set_result(None)

    async def _process(self, slot: Slot, task: str) -> None:
        name = slot.session.name
        slot.status, slot.task, slot.activity, slot.phase = "busy", task, None, None
        slot.last_error = None
        slot.subagents.clear()
        self._publish_status(slot)
        try:
            reply = await slot.session.run(task)
        except AgentError as e:
            log.warning("session %s failed: %s", name, e)
            slot.status, slot.last_error = "error", str(e)
            self._bus.publish("error", where=name, message=str(e))
            self._talker.notify(
                f"A sessão {name} não conseguiu terminar a tarefa. O motivo está no painel."
            )
        else:
            slot.status = "idle"
            slot.tasks_done += 1
            slot.tokens += reply.tokens
            slot.last_summary = reply.summary or None
            slot.context = reply.context or slot.context
            if reply.session_id:
                records.update_session(self._db, name, claude_session_id=reply.session_id)
            done = f"{name} terminou"
            self._talker.notify(f"{done}: {reply.summary}" if reply.summary else f"{done}.")
        slot.task, slot.activity, slot.phase = None, None, None
        slot.last_used = self._clock()
        self._publish_status(slot)

    def _apply(self, slot: Slot, event: dict[str, Any]) -> bool:
        kind = event["type"]
        if kind == "agent_progress":
            text = " ".join(str(event.get("label") or event.get("content") or "").split())
            slot.activity = text[:ACTIVITY_MAX] or None
            slot.phase = event.get("phase") or slot.phase
        elif kind == "subagent_started":
            slot.subagents[event["id"]] = SubagentView(
                id=event["id"],
                type=event.get("subagent_type") or "agente",
                description=event.get("description") or "",
            )
        elif kind == "subagent_progress" and (sub := slot.subagents.get(event["id"])):
            sub.last_tool = event.get("last_tool")
        elif kind == "subagent_finished" and (sub := slot.subagents.get(event["id"])):
            sub.status = event["status"]
        else:
            return False
        return True

    async def _stop(self, slot: Slot) -> None:
        if slot.worker is not None:
            slot.worker.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await slot.worker
        slot.waiting = False
        while not slot.queue.empty():
            slot.queue.get_nowait()
        await slot.session.disconnect()
        self._wake()

    def _get(self, name: str) -> Slot:
        owner = self._owner(name)
        if owner is None:
            raise SessionNotFound(f"Não existe sessão chamada {name}.")
        return self._slots[owner.lower()]

    def _owner(self, spoken: str, skip: str = "") -> str | None:
        """The session whose name or alias is `spoken`, ignoring case; `skip` is left out."""
        wanted = spoken.strip().lower()
        for record in records.list_sessions(self._db):
            if record.name.lower() == skip.lower():
                continue
            if wanted in (n.lower() for n in [record.name, *record.aliases]):
                return record.name
        return None

    def _check_aliases(self, name: str, aliases: Iterable[str]) -> builtins.list[str]:
        clean = [a.strip() for a in aliases if a.strip()]
        for alias in clean:
            if (owner := self._owner(alias, skip=name)) is not None:
                raise SessionError(f"O apelido {alias} já é da sessão {owner}.")
        return clean

    def _publish_status(self, slot: Slot) -> None:
        self._bus.publish("session_status", session=self._view(slot).model_dump())

    def _view(self, slot: Slot) -> SessionView:
        s = slot.session
        record = records.get_session(self._db, s.name)
        assert record is not None, s.name
        ws, proj = self._place(record)
        model, effort = self._settings.resolve(record.kind, record.model, record.effort)
        return SessionView(
            name=s.name,
            aliases=record.aliases,
            kind=s.kind.kind,
            label=s.kind.label,
            model=model,
            effort=effort,
            cwd=_short(Path(ws.path) if ws else self._home, self._home),
            project=proj.name if proj else None,
            workspace=ws.name if ws else None,
            branch=ws.branch if ws else None,
            status=slot.status,
            phase=slot.phase,
            task=slot.task,
            activity=slot.activity,
            queue=slot.queue.qsize(),
            waiting=slot.waiting,
            connected=s.connected,
            tasks_done=slot.tasks_done,
            tokens=slot.tokens,
            context_tokens=slot.context[0] if slot.context else None,
            context_max=slot.context[1] if slot.context else None,
            last_summary=slot.last_summary,
            last_error=slot.last_error,
            protected=slot.protected,
            subagents=list(slot.subagents.values()),
        )


def _check_effort(effort: str | None) -> None:
    if effort is not None and effort not in EFFORTS:
        raise SessionError(f"Effort inválido: {effort}. Use {', '.join(EFFORTS)}.")


def _short(path: Path, home: Path) -> str:
    try:
        rest = path.relative_to(home)
    except ValueError:
        return str(path)
    return "~" if rest == Path() else f"~/{rest}"
