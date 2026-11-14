from pathlib import Path

import pytest
import yaml

from config import load_config
from errors import ConfigError

EXAMPLE = Path(__file__).parent.parent / "config.example.yaml"


def test_loads_example_config() -> None:
    config = load_config(EXAMPLE)

    assert config.whisper.model == "large-v3-turbo"
    assert config.wakeword.model == "wakeword/alfred.onnx"
    assert config.wakeword.name == "Alfred"
    assert config.kokoro.acknowledgements[0] == "Certo."
    assert config.listener.silence_ms == 1800
    assert config.agents.timeout_s == 60


def test_missing_file_raises_config_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "nope.yaml")


def test_invalid_field_raises_config_error_naming_the_field(tmp_path: Path) -> None:
    bad = tmp_path / "config.yaml"
    bad.write_text(EXAMPLE.read_text().replace("threshold: 0.5", "threshold: high"))

    with pytest.raises(ConfigError, match=r"wakeword\.threshold"):
        load_config(bad)


def test_session_limit_comes_from_limits() -> None:
    assert load_config(EXAMPLE).limits.max_active_sessions == 3


def test_seeds_for_agents_limits_and_storage() -> None:
    config = load_config(EXAMPLE)

    assert config.agents.models == {"alfred": "sonnet", "geral": "sonnet", "implementacao": "opus"}
    assert config.limits.idle_minutes == 10
    assert config.storage.db_path == Path("data/alfred.sqlite3")
    assert config.seed_defaults().models["implementacao"] == "opus"


def test_models_default_to_the_default_model(tmp_path: Path) -> None:
    raw = yaml.safe_load(EXAMPLE.read_text())
    del raw["agents"]["models"]
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(raw))

    assert load_config(path).seed_defaults().models == {
        "alfred": "sonnet",
        "geral": "sonnet",
        "implementacao": "sonnet",
    }
