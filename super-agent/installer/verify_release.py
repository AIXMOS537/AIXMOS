"""Exercise a Windows release in a throwaway directory; no client config changes."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('installer', type=Path)
    a = ap.parse_args()
    exe = a.installer.resolve()
    with tempfile.TemporaryDirectory(prefix='aixmos-release-') as tmp:
        dest = Path(tmp) / "client's install"
        env = dict(os.environ, AIXMOS_NO_PREWARM='1')
        env.pop('AIXMOS_MEMDIR', None)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = str(sock.getsockname()[1])
        def run(cmd, **kwargs):
            p = subprocess.run([str(x) for x in cmd], env=env, capture_output=True,
                               text=True, encoding='utf-8', errors='replace', timeout=180,
                               creationflags=0x08000000, **kwargs)
            if p.returncode:
                raise RuntimeError(p.stdout + p.stderr)
            return p.stdout
        py, cli = dest / 'runtime/python.exe', dest / 'aixmos_local.py'
        setup = [exe, '--dir', dest, '--port', port, '--role', 'builder', '--quiet',
                 '--no-ollama', '--no-model', '--no-autostart', '--no-launch', '--no-shortcuts', '--no-mcp']
        try:
            run(setup)
            state = json.loads(run([py, cli, 'status', '--port', port]))
            assert state['version'] == '2.1.1'
            messages = [
                {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2025-11-25'}},
                {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call', 'params': {'name': 'write_file', 'arguments': {'path': 'proof.txt', 'content': 'installed proof'}}},
                {'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call', 'params': {'name': 'read_file', 'arguments': {'path': 'proof.txt'}}},
            ]
            result = run([py, cli, 'mcp', '--autonomy', 'builder'], input='\n'.join(map(json.dumps, messages)) + '\n')
            rows = [json.loads(x) for x in result.splitlines()]
            assert rows[-1]['result']['content'][0]['text'] == 'installed proof'
            cfg = Path(tmp) / 'mock-cursor.json'
            run([py, cli, 'pair', '--client', 'cursor', '--config', cfg])
            entry = json.loads(cfg.read_text())['mcpServers']['aixmos']
            assert entry['command'].lower() == str(py).lower()
            assert Path(entry['args'][0]) == cli
            # Verify the generated CMD launcher in a path with spaces and apostrophes.
            run(['cmd', '/d', '/c', str(dest / 'Status AIXMOS.cmd')])
            run([py, cli, 'stop', '--port', port])
            time.sleep(.5)
            run(setup)
            assert (dest / 'memory/workspace/proof.txt').read_text() == 'installed proof'
            assert json.loads(run([py, cli, 'status', '--port', port]))['version'] == '2.1.1'
            run([py, cli, 'stop', '--port', port])
            time.sleep(.5)
            print('PASS: fresh install, bundled Python, health, stdio write/read, pairing, CMD launcher, stop, upgrade, memory preservation')
        finally:
            if py.exists():
                subprocess.run([str(py), str(cli), 'stop', '--port', port], env=env,
                               capture_output=True, timeout=20, creationflags=0x08000000)
                time.sleep(.5)


if __name__ == '__main__':
    main()
