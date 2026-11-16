import os, subprocess, sys, json, wave
import numpy as np

FF = r"D:\opencodeall\work\ffmpeg-bink2\ffmpeg-bink2\ffmpeg.exe"
WORK = r"D:\opencodeall\work"
BK2 = os.path.join(WORK, "m01_700_cut.bk2")
SRC = r"D:\Steam\steamapps\common\Deus Ex Mankind Divided\runtime\E97D72A3B3C4A97B74B2F91DF27E67EB.pc_binkvid"

if not os.path.exists(BK2):
    d = open(SRC, 'rb').read()
    open(BK2, 'wb').write(d[24:])

audio_to_track = {i: "0x%x" % i for i in range(10)}
audio_to_track[10] = "0xc"
audio_to_track[11] = "0xd"

# 1. extract clips as 16 kHz mono 16-bit PCM (whisper native)
clips = {}
for ai in range(12):
    tid = audio_to_track[ai]
    out = os.path.join(WORK, "track16_%s.wav" % tid)
    r = subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-y", "-i", BK2,
                        "-ss", "10", "-t", "14", "-map", "0:a:%d" % ai, "-vn",
                        "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", out],
                       capture_output=True)
    ok = os.path.exists(out) and os.path.getsize(out) > 0
    clips[tid] = out
    print("extract", tid, "->", os.path.getsize(out) if ok else "FAIL", flush=True)


def load_pcm16(path):
    with wave.open(path, 'rb') as w:
        data = w.readframes(w.getnframes())
    a = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
    return a


from faster_whisper import WhisperModel
model = WhisperModel("tiny", device="cpu", compute_type="int8")
print("model loaded", flush=True)

results = {}
for tid in sorted(clips, key=lambda x: int(x, 16)):
    try:
        audio = load_pcm16(clips[tid])
        segments, info = model.transcribe(audio, language=None, beam_size=1,
                                          condition_on_previous_text=False,
                                          vad_filter=False)
        _ = next(segments, None)
        lang = getattr(info, "language", None)
        prob = getattr(info, "language_probability", None)
        results[tid] = {"language": lang, "prob": round(float(prob), 3) if prob is not None else None}
        print("track", tid, "->", lang, "prob", results[tid]["prob"], flush=True)
    except Exception as e:
        results[tid] = {"language": None, "error": repr(e)}
        print("track", tid, "ERROR", repr(e), flush=True)

json.dump(results, open(os.path.join(WORK, "track_langs.json"), "w"), indent=2)
print("DONE", flush=True)
