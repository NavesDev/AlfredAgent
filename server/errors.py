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


class ProjectError(AlfredError):
    """Invalid request about projects or workspaces. The message is pt-BR: Alfred speaks it."""


class ProjectNotFound(ProjectError):
    """No project or workspace with that name or id."""


class ProjectInUse(ProjectError):
    """Cannot delete: workspaces or sessions still depend on it, or the worktree is dirty."""


class GitError(AlfredError):
    """A git command failed. The message is git's stderr, trimmed."""


class SettingsError(AlfredError):
    """Invalid settings from the panel. The message is pt-BR."""
