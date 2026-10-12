"""Layered exceptions. See docs/ARCHITECTURE.md#erros."""


class AlfredError(Exception):
    """Base for every error Alfred raises on purpose."""


class ConfigError(AlfredError):
    """Invalid or missing config. Fatal at startup."""


class DependencyError(AlfredError):
    """Missing external dependency (claude CLI, audio device, model). Fatal at startup."""


class AudioError(AlfredError):
    """Capture, STT or TTS failure. Recoverable per turn."""


class AgentError(AlfredError):
    """Agent SDK failure or timeout. Recoverable per turn."""


class SessionError(AlfredError):
    """Invalid request about named sessions. The message is pt-BR: Alfred speaks it."""


class SessionNotFound(SessionError):
    """No session with that name."""


class SessionProtected(SessionError):
    """The session cannot be deleted (it can still be cleared)."""
