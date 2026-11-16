import os, subprocess, sys, wave
import numpy as np

FF = r"D:\opencodeall\work\ffmpeg-bink2\ffmpeg-bink2\ffmpeg.exe"
WORK = r"D:\opencodeall\work"
BK2 = os.path.join(WORK, "m01_700_cut.bk2")

audio_to_track = {i: "0x%x" % i for i in range(10)}
audio_to_track[10] = "0xc"
audio_to_track[11] = "0xd"

# focus on uncertain tracks + re-verify 0x4
focus = [0, 1, 2, 3, 4]


def load_pcm16(path):
    with wave.open(path, 'rb') as w:
        data = w.readframes(w.getnframes())
    return np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0


from faster_whisper import WhisperModel
model = WhisperModel("tiny", device="cpu", compute_type="int8")

for ai in focus:
    tid = audio_to_track[ai]
    out = os.path.join(WORK, "track16_long_%s.wav" % tid)
    subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-y", "-i", BK2,
                    "-ss", "35", "-t", "40", "-map", "0:a:%d" % ai, "-vn",
                    "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", out], capture_output=True)
    audio = load_pcm16(out)
    segments, info = model.transcribe(audio, language=None, beam_size=1,
                                      condition_on_previous_text=False, vad_filter=False)
    text = " ".join(s.text.strip() for s in segments)
    print("track %s -> lang=%s prob=%s | text=%r" % (
        tid, getattr(info, "language", "?"),
        round(float(getattr(info, "language_probability", 0)), 3), text[:120]), flush=True)

print("DONE", flush=True)
