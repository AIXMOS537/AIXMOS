"""Per-user lifecycle and non-destructive client pairing."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import webbrowser
from . import settings

ROOT = Path(settings.ROOT)
ENTRY = ROOT / 'aixmos_local.py'


def identity():
    return hashlib.sha256((os.path.normcase(os.path.realpath(ROOT)) + '|' +
                           os.path.normcase(os.path.realpath(settings.MEMDIR))).encode()).hexdigest()


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
            f.write('\n')
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def request(port, path='/api/health', token=None):
    headers = {'X-AIXMOS-Control': token} if token else {}
    req = urllib.request.Request('http://127.0.0.1:%d%s' % (port, path),
                                 data=b'{}' if token else None, headers=headers)
    # Local lifecycle operations never use a corporate/ambient HTTP proxy.
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=2) as r:
        return json.load(r)


def health(port):
    try:
        result = request(port)
        return result if result.get('app') == 'AIXMOS' and result.get('installation') == identity() else None
    except (OSError, ValueError):
        return None


def state_path(port):
    return Path(settings.MEMDIR) / ('runtime-%d.json' % port)


def start(port):
    if health(port):
        return
    with socket.socket() as sock:
        if sock.connect_ex(('127.0.0.1', port)) == 0:
            raise RuntimeError('Port %d belongs to another service or older AIXMOS. Choose another --port.' % port)
    token = secrets.token_urlsafe(32)
    env = dict(os.environ, AIXMOS_CONTROL_TOKEN=token)
    Path(settings.MEMDIR).mkdir(parents=True, exist_ok=True)
    logpath = Path(settings.MEMDIR) / 'server.log'
    options = {'creationflags': 0x08000000 | 0x00000008} if os.name == 'nt' else {'start_new_session': True}
    with open(logpath, 'ab') as log:
        child = subprocess.Popen([sys.executable, str(ROOT / 'project_aixmos_server.py'), str(port)],
                                 cwd=ROOT, env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=log, **options)
    for _ in range(80):
        live = health(port)
        if live and live.get('pid') == child.pid:
            atomic_json(state_path(port), {'pid': child.pid, 'token': token})
            return
        if child.poll() is not None:
            break
        time.sleep(.25)
    if child.poll() is None:
        child.terminate()  # Only our own subprocess, never a PID found by port.
        child.wait(timeout=10)
    raise RuntimeError('AIXMOS failed to start; inspect ' + str(logpath))


def stop(port):
    live = health(port)
    if not live:
        raise RuntimeError('This installation is not responding; no process was stopped.')
    state = json.loads(state_path(port).read_text(encoding='utf-8'))
    if state.get('pid') != live.get('pid'):
        raise RuntimeError('Runtime ownership changed; no process was stopped.')
    request(port, '/api/runtime/stop', state['token'])
    for _ in range(40):
        if not health(port):
            state_path(port).unlink(missing_ok=True)
            return
        time.sleep(.25)
    raise RuntimeError('Shutdown did not complete; no force-kill was attempted.')


def config_entry(autonomy='safe', roots=(), allow_shell=False):
    args = [str(ENTRY), 'mcp', '--autonomy', autonomy]
    for root in roots:
        args += ['--root', str(Path(root).resolve())]
    if allow_shell:
        args.append('--allow-shell')
    return {'command': sys.executable, 'args': args}


def merge_config(path, entry, replace=False):
    path = Path(path)
    data = json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else {}
    if not isinstance(data, dict) or not isinstance(data.get('mcpServers', {}), dict):
        raise ValueError('Existing config is not a valid MCP object; unchanged')
    servers = data.setdefault('mcpServers', {})
    if servers.get('aixmos') == entry:
        return 'already paired'
    if 'aixmos' in servers and not replace:
        raise ValueError('An AIXMOS entry already exists. Review it, then use --replace to back it up and replace it.')
    if path.exists():
        shutil.copy2(path, path.with_name(path.name + '.backup-' + str(time.time_ns())))
    servers['aixmos'] = entry
    atomic_json(path, data)
    return 'paired'


def claude_command():
    exe = shutil.which('claude')
    if not exe:
        raise RuntimeError('Claude Code is not installed or is missing from PATH.')
    if Path(exe).suffix.lower() in ('.cmd', '.bat', '.ps1'):
        # Invoke the npm entry point directly, so shell metacharacters in an
        # allowed folder cannot become commands through a Windows shim.
        package = Path(exe).parent / 'node_modules/@anthropic-ai/claude-code'
        native = package / 'bin/claude.exe'
        if native.is_file():
            return [str(native)]
        script = package / 'cli.js'
        node = shutil.which('node')
        if not node or not script.is_file():
            raise RuntimeError('Unsupported Claude shell shim. Install the native Claude CLI or import aixmos-mcp.json manually.')
        return [node, str(script)]
    return [exe]


def main():
    parser = argparse.ArgumentParser(description='AIXMOS local agent and client pairing')
    sub = parser.add_subparsers(dest='action', required=True)
    for name in ('start', 'stop', 'status'):
        p = sub.add_parser(name)
        p.add_argument('--port', type=int, default=8770)
        if name == 'start':
            p.add_argument('--open', action='store_true')
    for name in ('mcp', 'pair'):
        p = sub.add_parser(name)
        p.add_argument('--autonomy', choices=('safe', 'builder'), default='safe')
        p.add_argument('--root', action='append', default=[])
        p.add_argument('--allow-shell', action='store_true', help='Allow commands with normal user privileges; not sandboxed')
        if name == 'pair':
            p.add_argument('--client', choices=('cursor', 'claude-desktop', 'claude-code', 'json'), default='json')
            p.add_argument('--replace', action='store_true')
            p.add_argument('--config', type=Path, help='Explicit config path (Cursor/Desktop/JSON)')
    args = parser.parse_args()
    try:
        if hasattr(args, 'port') and not 1024 <= args.port <= 65535:
            raise ValueError('port must be between 1024 and 65535')
        for root in getattr(args, 'root', []):
            if not Path(root).is_dir():
                raise ValueError('Allowed root must be an existing folder: ' + root)
        if args.action == 'mcp':
            from .mcp_local import serve
            serve(args.autonomy, [str(Path(r).resolve()) for r in args.root], args.allow_shell)
        elif args.action == 'start':
            start(args.port)
            if args.open:
                webbrowser.open('http://localhost:%d' % args.port)
            print('AIXMOS is running at http://localhost:%d' % args.port)
        elif args.action == 'stop':
            stop(args.port)
            print('AIXMOS stopped.')
        elif args.action == 'status':
            result = health(args.port)
            print(json.dumps(result or {'app': 'AIXMOS', 'running': False}, indent=2))
            if not result:
                raise SystemExit(1)
        elif args.action == 'pair':
            entry = config_entry(args.autonomy, args.root, args.allow_shell)
            if args.client == 'claude-code':
                # Let Claude validate conflicts; never remove a working registration first.
                result = subprocess.run([*claude_command(), 'mcp', 'add', '--transport', 'stdio', '--scope', 'user',
                                         'aixmos', '--', entry['command'], *entry['args']])
                raise SystemExit(result.returncode)
            if args.client == 'json' and not args.config:
                print(json.dumps({'mcpServers': {'aixmos': entry}}, indent=2))
                return
            path = args.config
            if path is None and args.client == 'cursor':
                path = Path.home() / '.cursor' / 'mcp.json'
            if path is None and args.client == 'claude-desktop':
                if sys.platform == 'win32':
                    path = Path(os.environ['APPDATA']) / 'Claude' / 'claude_desktop_config.json'
                elif sys.platform == 'darwin':
                    path = Path.home() / 'Library/Application Support/Claude/claude_desktop_config.json'
                else:
                    raise ValueError('Use --config for your Claude Desktop config on this platform.')
            print(merge_config(path, entry, args.replace) + ': ' + str(path))
            print('Restart the client and approve AIXMOS tools when prompted.')
    except (OSError, ValueError, RuntimeError) as exc:
        print('AIXMOS: ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
