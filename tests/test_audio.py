import wave

import numpy as np

from site_feedback.__main__ import load_wav_16k


def test_wav_is_decoded_without_pyav_and_resampled_to_16k(tmp_path):
    # 2026-10-27: faster-whisper's own decoder crashed on PyAV 16 (metadata_errors TypeError).
    rate = 48000
    tone = (np.sin(np.linspace(0, 2 * np.pi * 440, rate)) * 16000).astype(np.int16)  # 1 s
    p = tmp_path / "a.wav"
    with wave.open(str(p), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(tone.tobytes())
    x = load_wav_16k(p)
    assert x.dtype == np.float32
    assert len(x) == 16000
    assert 0.4 < np.abs(x).max() <= 1.0
