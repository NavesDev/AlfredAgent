"""Settings for the panel: model and effort per kind, limits, disabled MCP servers."""

from fastapi import APIRouter, HTTPException, Request

from controllers.settings import Settings, SettingsUpdate, SettingsView
from errors import SettingsError

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


@router.get("")
async def get_settings(request: Request) -> SettingsView:
    return _settings(request).get()


@router.put("")
async def update_settings(body: SettingsUpdate, request: Request) -> SettingsView:
    try:
        return _settings(request).update(body)
    except SettingsError as e:
        raise HTTPException(422, str(e)) from e
