#!/usr/bin/env python3
"""AIXMOS — local voice-commanded assistant. Your voice is the key.

Pipeline: mic -> speaker verification (voiceprint) -> Whisper STT -> route:
  * "code ..."  -> opencode run (your free local coding agent)
  * anything else -> Ollama chat (local LLM), reply spoken by Kokoro TTS

All local. No cloud. Config in ~/aixmos/config.json (persona, voice, model).
"""
import argparse, json, os, subprocess, sys, time, urllib.request

import numpy as np
import soundfile as sf

SR = 16000
DIR = os.path.expanduser("~/aixmos")
PRINT_PATH = os.path.join(DIR, "voiceprint.npy")
CONF_PATH = os.path.join(DIR, "config.json")
KOKORO_DIR = os.path.expanduser("~/kokoro-tts")

DEFAULT_CONF = {
    "name": "AIXMOS",
    "persona": ("You are AIXMOS, the operations AI for TMMT, Project X and Hailmary. "
                "You are sharp, loyal, and concise. Answer in at most 4 sentences "
                "unless asked for detail."),
    "voice": "af_bella",
    "model": "qwen3-coder:30b",
    "threshold": 0.72,
}


def conf():
    os.makedirs(DIR, exist_ok=True)
    if not os.path.exists(CONF_PATH):
        json.dump(DEFAULT_CONF, open(CONF_PATH, "w"), indent=2)
    c = dict(DEFAULT_CONF)
    c.update(json.load(open(CONF_PATH)))
    return c


def record(seconds, prompt):
    import sounddevice as sd
    print(prompt, flush=True)
    audio = sd.rec(int(seconds * SR), samplerate=SR, channels=1, dtype="float32")
    sd.wait()
    return audio[:, 0]


def load_wav(path):
    data, sr = sf.read(path)
    if data.ndim > 1:
        data = data.mean(axis=1)
    if sr != SR:
        x = np.linspace(0, 1, int(len(data) * SR / sr))
        xp = np.linspace(0, 1, len(data))
        data = np.interp(x, xp, data)
    return data.astype("float32")


_encoder = None
def embed(wav):
    global _encoder
    from resemblyzer import VoiceEncoder, preprocess_wav
    if _encoder is None:
        _encoder = VoiceEncoder("cpu")
    e = _encoder.embed_utterance(preprocess_wav(wav, source_sr=SR))
    return e / np.linalg.norm(e)


def enroll(args):
    embs = []
    if args.wav:
        for p in args.wav:
            embs.append(embed(load_wav(p)))
    else:
        for i in range(3):
            input(f"Enrollment {i + 1}/3 — press Enter, then speak naturally for ~6s "
                  "(read any sentence)")
            embs.append(embed(record(6, "  recording...")))
    v = np.mean(embs, axis=0)
    v /= np.linalg.norm(v)
    np.save(PRINT_PATH, v)
    print(f"voiceprint saved -> {PRINT_PATH}")


def verify(wav, threshold):
    if not os.path.exists(PRINT_PATH):
        sys.exit("no voiceprint enrolled — run with --enroll first")
    sim = float(np.load(PRINT_PATH) @ embed(wav))
    return sim, sim >= threshold


_whisper = None
def transcribe(wav):
    global _whisper
    import whisper
    if _whisper is None:
        print("loading whisper (first time downloads ~140MB)...", flush=True)
        _whisper = whisper.load_model("base.en")
    return _whisper.transcribe(wav, fp16=False)["text"].strip()


def speak(text, voice):
    try:
        from kokoro_onnx import Kokoro
        k = Kokoro(os.path.join(KOKORO_DIR, "kokoro-v1.0.onnx"),
                   os.path.join(KOKORO_DIR, "voices-v1.0.bin"))
        samples, sr = k.create(text[:500], voice=voice, speed=1.0, lang="en-us")
        out = os.path.join(DIR, "reply.wav")
        sf.write(out, samples, sr)
        for player in (["afplay", out], ["aplay", "-q", out]):
            try:
                subprocess.run(player, check=True, capture_output=True)
                return
            except Exception:
                continue
    except Exception as e:
        print(f"(tts skipped: {e})")


def ask_ollama(text, c):
    body = json.dumps({
        "model": c["model"],
        "messages": [{"role": "system", "content": c["persona"]},
                     {"role": "user", "content": text}],
        "stream": False,
    }).encode()
    req = urllib.request.Request("http://localhost:11434/api/chat", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read())["message"]["content"]


def one_round(args, c):
    wav = load_wav(args.wav[0]) if args.wav else record(
        args.seconds, f"listening for {args.seconds}s — speak your command...")
    sim, ok = verify(wav, c["threshold"])
    print(f"voice match: {sim:.2f} (threshold {c['threshold']})")
    if not ok:
        print("ACCESS DENIED")
        speak("Voice not recognized. Access denied.", c["voice"])
        return False
    text = args.text or transcribe(wav)
    print(f"heard: {text!r}")
    if not text:
        return True
    lower = text.lower().strip()
    if lower.split()[0] in ("code", "coder", "coding"):
        task = text.split(" ", 1)[1] if " " in text else ""
        speak("On it. Handing off to the coding agent.", c["voice"])
        subprocess.run(["opencode", "run", task])
        return True
    reply = ask_ollama(text, c)
    print(f"\n{reply}\n")
    import re
    short = " ".join(re.split(r"(?<=[.!?])\s+", reply)[:3])[:500]
    speak(short or "Done.", c["voice"])
    return True


def main():
    ap = argparse.ArgumentParser(description="AIXMOS voice assistant")
    ap.add_argument("--enroll", action="store_true", help="record your voiceprint")
    ap.add_argument("--loop", action="store_true", help="keep listening")
    ap.add_argument("--seconds", type=int, default=6)
    ap.add_argument("--wav", nargs="+", help="use wav file(s) instead of mic")
    ap.add_argument("--text", help="override transcription (testing)")
    args = ap.parse_args()
    c = conf()
    if args.enroll:
        enroll(args)
        return
    if args.loop:
        while True:
            input("\n[AIXMOS] press Enter to talk (Ctrl-C to quit)")
            one_round(args, c)
    else:
        one_round(args, c)


if __name__ == "__main__":
    main()
