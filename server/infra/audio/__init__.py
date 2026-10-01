import numpy as np


def level(samples: np.ndarray) -> float:
    """Loudness in 0..1 for UI animation; samples are float in [-1, 1]."""
    return min(1.0, float(np.sqrt(np.mean(np.square(samples)))) * 4)


def check_audio(input_rate: int, output_rate: int = 24000) -> None:
    """Fail fast if PortAudio or the default mic/speaker is unavailable."""
    from errors import DependencyError

    try:
        import sounddevice as sd

        sd.check_input_settings(samplerate=input_rate, channels=1, dtype="int16")
        sd.check_output_settings(samplerate=output_rate, channels=1, dtype="float32")
    except Exception as e:
        raise DependencyError(f"audio device unavailable: {e}") from e
