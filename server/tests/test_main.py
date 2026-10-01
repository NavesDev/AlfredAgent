import sys
import types
from pathlib import Path

import pytest

import main
from errors import DependencyError
from infra.audio import check_audio


def test_invalid_config_exits_1_with_message(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main.main(tmp_path / "missing.yaml") == 1
    assert "config not found" in capsys.readouterr().err


def test_missing_dependency_exits_1(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def boom() -> None:
        raise DependencyError("claude CLI not found")

    monkeypatch.setattr(main, "check_cli", boom)

    assert main.main(Path(__file__).parent.parent / "config.example.yaml") == 1
    assert "claude CLI not found" in capsys.readouterr().err


def test_check_audio_wraps_device_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def no_device(**_: object) -> None:
        raise OSError("no default input device")

    fake = types.SimpleNamespace(check_input_settings=no_device, check_output_settings=no_device)
    monkeypatch.setitem(sys.modules, "sounddevice", fake)

    with pytest.raises(DependencyError, match="no default input device"):
        check_audio(16000)
