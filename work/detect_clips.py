import subprocess, wave, os
import numpy as np

FF = r"D:\opencodeall\work\ffmpeg-bink2\ffmpeg-bink2\ffmpeg.exe"
CIN = r"D:\opencodeall\cinematics"

# folder -> track id (current, possibly wrong, labels)
FOLDER_TRACK = {
    'en': '0x0', 'ja': '0x1', 'fr': '0x2', 'it': '0x3', 'de': '0x4',
    'es': '0x5', 'ru': '0x6', 'pl': '0x7', 'mx': '0x8', 'pt': '0x9',
    'extra_c': '0xc', 'extra_d': '0xd',
}

targets = [
    r"cinematiques\24_metro_transition\mp1_metro_asimov_enter_old_district.wav",
    r"cinematiques\98_jensen_appt\prague1\m98_app2_cut_shower.wav",
    r"cinematiques\10_cutscenes\10_dubai\m01_500_cut\m01_500_cut.wav",
]


def to_mono16(src, dst):
    subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-y", "-i", src,
                    "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", dst], capture_output=True)


def load_pcm16(path):
    with wave.open(path, 'rb') as w:
        data = w.readframes(w.getnframes())
    return np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0


from faster_whisper import WhisperModel
model = WhisperModel("tiny", device="cpu", compute_type="int8")

for rel in targets:
    print("=== %s ===" % rel.replace("\\", "/").split("/")[-1], flush=True)
    for folder, tid in sorted(FOLDER_TRACK.items(), key=lambda kv: int(kv[1], 16)):
        src = os.path.join(CIN, folder, rel)
        if not os.path.exists(src):
            continue
        tmp = os.path.join(r"D:\opencodeall\work", "det_tmp.wav")
        to_mono16(src, tmp)
        audio = load_pcm16(tmp)
        segments, info = model.transcribe(audio, language=None, beam_size=1,
                                          condition_on_previous_text=False, vad_filter=False)
        text = " ".join(s.text.strip() for s in segments)
        print("  track %s (folder %-8s) -> lang=%s prob=%.2f | %r" % (
            tid, folder, getattr(info, "language", "?"),
            float(getattr(info, "language_probability", 0)), text[:90]), flush=True)
print("DONE", flush=True)
