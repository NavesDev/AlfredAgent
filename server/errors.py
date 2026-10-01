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
