"""Runs tasks Alfred delegates, one at a time per session, and speaks the result."""

import asyncio
from typing import Protocol

from errors import AgentError
from events import EventBus
from infra.claude.alfred import Reply


class Session(Protocol):
    name: str

    async def run(self, task: str) -> Reply: ...


class Speaker(Protocol):
    def say(self, text: str) -> None: ...


class Sessions:
    def __init__(self, bus: EventBus, talker: Speaker, session: Session) -> None:
        self._bus, self._talker, self._session = bus, talker, session
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._busy = False

    def delegate(self, task: str) -> str:
        """Called by Alfred's tool; returns right away with what to tell the user."""
        ahead = self._queue.qsize() + self._busy
        self._queue.put_nowait(task)
        name = self._session.name
        if ahead:
            return f"A sessão {name} está ocupada; a tarefa entrou na fila (posição {ahead})."
        return f"Tarefa enviada para a sessão {name}. Ela avisa por voz quando terminar."

    async def run(self) -> None:
        while True:
            await self.process_one(await self._queue.get())

    async def process_one(self, task: str) -> None:
        name = self._session.name
        self._busy = True
        self._bus.publish("session_status", session=name, status="busy")
        try:
            reply = await self._session.run(task)
        except AgentError as e:
            self._bus.publish("error", where=name, message=str(e))
            self._talker.say(f"A sessão {name} não conseguiu terminar a tarefa.")
        else:
            self._talker.say(reply.summary or f"A sessão {name} terminou.")
        finally:
            self._busy = False
            self._bus.publish("session_status", session=name, status="idle")
