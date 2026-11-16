import subprocess, wave, os
import numpy as np
FF = r"D:\opencodeall\work\ffmpeg-bink2\ffmpeg-bink2\ffmpeg.exe"
CIN = r"D:\opencodeall\cinematics"

checks = {
    'en': r"cinematiques\10_cutscenes\10_dubai\m01_700_cut\m01_700_cut.wav",
    'ru': r"cinematiques\10_cutscenes\10_dubai\m01_700_cut\m01_700_cut.wav",
    'mx': r"cinematiques\10_cutscenes\10_dubai\m01_700_cut\m01_700_cut.wav",
    'pt': r"cinematiques\10_cutscenes\10_dubai\m01_700_cut\m01_700_cut.wav",
}

def to_mono16(src, dst):
    subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-y", "-i", src,
                    "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", dst], capture_output=True)

def load_pcm16(path):
    with wave.open(path, 'rb') as w:
        data = w.readframes(w.getnframes())
    return np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0

from faster_whisper import WhisperModel
model = WhisperModel("tiny", device="cpu", compute_type="int8")

for folder, rel in checks.items():
    src = os.path.join(CIN, folder, rel)
    tmp = r"D:\opencodeall\work\ver_tmp.wav"
    to_mono16(src, tmp)
    audio = load_pcm16(tmp)
    segments, info = model.transcribe(audio, language=None, beam_size=1,
                                      condition_on_previous_text=False, vad_filter=False)
    text = " ".join(s.text.strip() for s in segments)
    # avoid cp1251 console errors: encode-safe
    print("folder %-3s -> lang=%s prob=%.2f | %s" % (
        folder, getattr(info, "language", "?"),
        float(getattr(info, "language_probability", 0)),
        text[:70].encode("ascii", "replace").decode()), flush=True)
print("VERIFY DONE", flush=True)
