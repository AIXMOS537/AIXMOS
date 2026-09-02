#!/usr/bin/env python3
"""
Project Crimson Shadow -- local chat server WITH PERSISTENT MEMORY.

Serves index.html at "/" and talks to the local Ollama daemon
(http://localhost:11434). Every message is saved to memory/conversation.json,
so the assistant remembers previous chats across reloads, restarts and reboots.

Endpoints:
  GET  /                 -> the chat UI
  GET  /api/tags         -> proxied to Ollama (model list)
  GET  /api/memory       -> {"messages":[...]}  the full saved conversation
  POST /api/chat         -> body {model, content}; streams reply, persists both turns
  POST /api/forget       -> wipes the saved conversation

Binds to 127.0.0.1 only (local, private). Ctrl+C to stop.
"""
import os, sys, json, threading, subprocess, tempfile, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import context_tools  # safe live-context layer: time / location / weather / system stats

OLLAMA   = "http://localhost:11434"
DIR      = os.path.dirname(os.path.abspath(__file__))
MEMDIR   = os.path.join(DIR, "memory")
MEMFILE  = os.path.join(MEMDIR, "conversation.json")
LOCK     = threading.Lock()
# --- Fully-local speech-to-text (whisper.cpp, CPU) ---
WHISPER_CLI   = os.path.join(DIR, "whisper", "bin", "Release", "whisper-cli.exe")
WHISPER_MODEL = os.path.join(DIR, "whisper", "models", "ggml-base.en.bin")
STT_LOCK      = threading.Lock()   # serialize transcription (2-core CPU)
MAX_CTX_MSGS = 40      # most-recent messages fed into the model each turn
NUM_CTX      = 8192    # token context window requested from Ollama

_MEM_CACHE = {"mtime": None, "data": None}

def load_mem():
    try:
        mtime = os.path.getmtime(MEMFILE)
        if _MEM_CACHE["mtime"] == mtime and _MEM_CACHE["data"] is not None:
            return _MEM_CACHE["data"]
        with open(MEMFILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        _MEM_CACHE["mtime"], _MEM_CACHE["data"] = mtime, data
        return data
    except (OSError, ValueError):
        return []

def save_mem(msgs):
    os.makedirs(MEMDIR, exist_ok=True)
    tmp = MEMFILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(msgs, f, ensure_ascii=False, indent=1)
    os.replace(tmp, MEMFILE)   # atomic
    _MEM_CACHE["mtime"], _MEM_CACHE["data"] = os.path.getmtime(MEMFILE), msgs

def _err(e):
    return json.dumps({"error": str(e)}).encode()
SYSTEM   = ("You are Crimson Shadow, a private AI assistant running locally on the "
            "user's own machine. You retain persistent memory of previous conversations "
            "with this user; use that history for continuity and recall when relevant.")

class Handler(BaseHTTPRequestHandler):
    def _send(self, code, ctype, data=b""):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        if data:
            self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if data:
            self.wfile.write(data)

    def _index(self):
        try:
            with open(os.path.join(DIR, "index.html"), "rb") as f:
                self._send(200, "text/html; charset=utf-8", f.read())
        except OSError:
            self._send(500, "text/plain", b"index.html missing")

    def _proxy_get(self):
        try:
            resp = urllib.request.urlopen(OLLAMA + self.path, timeout=30)
            self._send(200, resp.headers.get("Content-Type", "application/json"), resp.read())
        except urllib.error.URLError as e:
            self._send(502, "application/json", _err(e))

    def _chat(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        try:
            req = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            req = {}
        model = req.get("model") or "qwen2.5:3b"
        content = (req.get("content") or "").strip()
        if not content:
            self._send(400, "application/json", b'{"error":"empty message"}'); return

        # Persist the user's turn, then build bounded context from full memory
        with LOCK:
            mem = load_mem()
            mem.append({"role": "user", "content": content})
            save_mem(mem)
        try:
            sys_prompt = SYSTEM + "\n\n" + context_tools.build_context()
        except Exception:
            sys_prompt = SYSTEM
        ctx = [{"role": "system", "content": sys_prompt}] + mem[-MAX_CTX_MSGS:]

        payload = json.dumps({"model": model, "messages": ctx, "stream": True,
                              "options": {"num_ctx": NUM_CTX}}).encode()
        r = urllib.request.Request(OLLAMA + "/api/chat", data=payload, method="POST")
        r.add_header("Content-Type", "application/json")
        try:
            resp = urllib.request.urlopen(r, timeout=600)
        except urllib.error.URLError as e:
            self._send(502, "application/json", _err(e)); return

        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson")
        self.end_headers()
        acc, buf = "", b""
        while True:
            chunk = resp.read(512)
            if not chunk:
                break
            try:
                self.wfile.write(chunk); self.wfile.flush()   # stream to browser
            except (BrokenPipeError, ConnectionResetError):
                break
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = (json.loads(line).get("message") or {})
                    if msg.get("content"):
                        acc += msg["content"]
                except ValueError:
                    pass
        # Persist the assistant's reply (reuse `mem` already in scope — no second read)
        if acc:
            with LOCK:
                mem.append({"role": "assistant", "content": acc})
                save_mem(mem)

    def _stt(self):
        """Fully-local speech-to-text: receive a WAV, run whisper.cpp, return text."""
        if not (os.path.exists(WHISPER_CLI) and os.path.exists(WHISPER_MODEL)):
            self._send(503, "application/json", b'{"error":"whisper not installed"}'); return
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length <= 0 or length > 25 * 1024 * 1024:
            self._send(400, "application/json", b'{"error":"bad audio size"}'); return
        audio = self.rfile.read(length)
        tmpdir = tempfile.mkdtemp(prefix="cs_stt_")
        wav = os.path.join(tmpdir, "in.wav")
        base = os.path.join(tmpdir, "out")
        text = ""
        try:
            with open(wav, "wb") as f:
                f.write(audio)
            with STT_LOCK:
                subprocess.run(
                    [WHISPER_CLI, "-m", WHISPER_MODEL, "-f", wav, "-nt", "-np", "-otxt", "-of", base],
                    capture_output=True, timeout=180, cwd=os.path.dirname(WHISPER_CLI))
            try:
                with open(base + ".txt", "r", encoding="utf-8") as f:
                    text = f.read().strip()
            except OSError:
                text = ""
        except (subprocess.TimeoutExpired, OSError) as e:
            self._send(500, "application/json", json.dumps({"error": str(e)}).encode()); return
        finally:
            for p in (wav, base + ".txt"):
                try: os.remove(p)
                except OSError: pass
            try: os.rmdir(tmpdir)
            except OSError: pass
        self._send(200, "application/json", json.dumps({"text": text}).encode())

    def _forget(self):
        with LOCK:
            try:
                os.remove(MEMFILE)
            except OSError:
                pass
            _MEM_CACHE["mtime"], _MEM_CACHE["data"] = None, None
        self._send(200, "application/json", b'{"ok":true}')

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._index()
        elif self.path == "/api/memory":
            self._send(200, "application/json",
                       json.dumps({"messages": load_mem()}, ensure_ascii=False).encode())
        elif self.path.startswith("/api/"):
            self._proxy_get()
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/api/chat":
            self._chat()
        elif self.path == "/api/stt":
            self._stt()
        elif self.path == "/api/forget":
            self._forget()
        else:
            self.send_error(404)

    def log_message(self, *a):
        pass

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8770
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=context_tools.prewarm, daemon=True).start()  # warm geo/weather cache
    n = len(load_mem())
    print("=" * 52)
    print("  PROJECT CRIMSON SHADOW  (persistent memory)")
    print("  Chat UI  ->  http://localhost:%d" % port)
    print("  Memory   ->  %s  (%d msgs)" % (MEMFILE, n))
    print("  (Ctrl+C to stop)")
    print("=" * 52)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n  Crimson Shadow stopped.")
        srv.shutdown()
