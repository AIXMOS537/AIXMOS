"""Real transport and lifecycle checks with isolated client config and data."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


class LocalAgent(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='aixmos-local-test-')
        self.base = Path(self.tmp.name)
        self.env = dict(os.environ, AIXMOS_MEMDIR=str(self.base / 'memory'), AIXMOS_NO_PREWARM='1')

    def tearDown(self):
        self.tmp.cleanup()

    def cli(self, *args, **kw):
        return subprocess.run([sys.executable, str(ROOT / 'aixmos_local.py'), *args],
                              cwd=self.base, env=self.env, capture_output=True, text=True,
                              encoding='utf-8', timeout=40, **kw)

    def mcp(self, calls, *flags):
        init = {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
                'params': {'protocolVersion': '2025-11-25'}}
        data = '\n'.join(json.dumps(x) for x in [init, *calls]) + '\n'
        p = self.cli('mcp', *flags, input=data)
        self.assertEqual(p.returncode, 0, p.stderr)
        return [json.loads(line) for line in p.stdout.splitlines()]

    def call(self, name, args=None):
        return {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call',
                'params': {'name': name, 'arguments': args or {}}}

    def test_stdio_protocol_and_default_permissions(self):
        rows = self.mcp([{'jsonrpc': '2.0', 'method': 'notifications/initialized'},
                         {'jsonrpc': '2.0', 'id': 3, 'method': 'tools/list'}, self.call('aixmos_status')])
        self.assertEqual(len(rows), 3)
        names = {t['name'] for t in rows[1]['result']['tools']}
        self.assertIn('read_file', names)
        self.assertNotIn('write_file', names)
        self.assertNotIn('run_command', names)
        self.assertEqual(rows[0]['result']['protocolVersion'], '2025-11-25')
        status = json.loads(rows[-1]['result']['content'][0]['text'])
        self.assertFalse(status['local_model_required'])

    def test_builder_write_read_and_escape_denied(self):
        rows = self.mcp([self.call('write_file', {'path': 'proof.txt', 'content': 'AIXMOS proof'}),
                         self.call('read_file', {'path': 'proof.txt'}),
                         self.call('read_file', {'path': str(self.base / 'outside.txt')})], '--autonomy', 'builder')
        self.assertFalse(rows[1]['result']['isError'])
        self.assertEqual(rows[2]['result']['content'][0]['text'], 'AIXMOS proof')
        self.assertTrue(rows[3]['result']['isError'])

    def test_explicit_root(self):
        (self.base / 'example.txt').write_text('granted')
        rows = self.mcp([self.call('read_file', {'path': str(self.base / 'example.txt')})], '--root', str(self.base))
        self.assertEqual(rows[-1]['result']['content'][0]['text'], 'granted')

    def test_shell_requires_explicit_flag(self):
        rows = self.mcp([self.call('run_python', {'code': 'print(7*6)'})], '--autonomy', 'builder')
        self.assertEqual(rows[-1]['error']['code'], -32602)
        rows = self.mcp([self.call('run_python', {'code': 'print(7*6)'})], '--autonomy', 'builder', '--allow-shell')
        self.assertIn('42', rows[-1]['result']['content'][0]['text'])

    def test_malformed_requests_and_invalid_arguments(self):
        p = self.cli('mcp', input='bad json\n[]\n')
        self.assertEqual([json.loads(x)['error']['code'] for x in p.stdout.splitlines()], [-32700, -32600])
        rows = self.mcp([self.call('read_file', {'path': []}), self.call('no-such-tool')])
        self.assertTrue(all(r['error']['code'] == -32602 for r in rows[1:]))

    def test_pair_preserves_config_and_is_idempotent(self):
        cfg = self.base / 'mcp.json'
        cfg.write_text(json.dumps({'otherSetting': True, 'mcpServers': {'existing': {'command': 'keep'}}}))
        p = self.cli('pair', '--client', 'cursor', '--config', str(cfg))
        self.assertEqual(p.returncode, 0, p.stderr)
        data = json.loads(cfg.read_text())
        self.assertTrue(data['otherSetting'])
        self.assertEqual(data['mcpServers']['existing']['command'], 'keep')
        p = self.cli('pair', '--client', 'cursor', '--config', str(cfg))
        self.assertIn('already paired', p.stdout)
        self.assertEqual(len(list(self.base.glob('mcp.json.backup-*'))), 1)

    def test_pair_conflict_and_invalid_config_stay_intact(self):
        cfg = self.base / 'mcp.json'
        for text in ('invalid', '{"mcpServers":{"aixmos":{"command":"keep"}}}'):
            cfg.write_text(text)
            p = self.cli('pair', '--client', 'cursor', '--config', str(cfg))
            self.assertNotEqual(p.returncode, 0)
            self.assertEqual(cfg.read_text(), text)

    def test_pair_replace_creates_backup(self):
        cfg = self.base / 'mcp.json'
        original = '{"mcpServers":{"aixmos":{"command":"old"}}}'
        cfg.write_text(original)
        p = self.cli('pair', '--client', 'cursor', '--config', str(cfg), '--replace')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(next(self.base.glob('mcp.json.backup-*')).read_text(), original)

    def test_claude_native_and_javascript_npm_layouts(self):
        code = '''
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0, sys.argv[1])
from aixmos.local_cli import claude_command
base = Path(sys.argv[2])
package = base / 'node_modules/@anthropic-ai/claude-code'
native = package / 'bin/claude.exe'
native.parent.mkdir(parents=True)
native.touch()
with patch('aixmos.local_cli.shutil.which', side_effect=lambda name: str(base / ('claude.cmd' if name == 'claude' else 'node.exe'))):
    assert claude_command() == [str(native)]
    native.unlink()
    script = package / 'cli.js'
    script.touch()
    assert claude_command() == [str(base / 'node.exe'), str(script)]
'''
        p = subprocess.run([sys.executable, '-c', code, str(ROOT), str(self.base)],
                           env=self.env, capture_output=True, text=True, timeout=10)
        self.assertEqual(p.returncode, 0, p.stderr)

    def test_lifecycle_start_identity_stop_and_memory_preserved(self):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = str(sock.getsockname()[1])
        try:
            p = self.cli('start', '--port', port)
            self.assertEqual(p.returncode, 0, p.stderr)
            p = self.cli('status', '--port', port)
            self.assertEqual(p.returncode, 0, p.stderr)
            first = json.loads(p.stdout)['pid']
            p = self.cli('start', '--port', port)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertEqual(first, json.loads(self.cli('status', '--port', port).stdout)['pid'])
            req = urllib.request.Request('http://127.0.0.1:' + port + '/api/runtime/stop', data=b'{}')
            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(req, timeout=3)
            self.assertEqual(error.exception.code, 403)
            error.exception.close()
            sentinel = self.base / 'memory' / 'keep.txt'
            sentinel.write_text('client data')
            p = self.cli('stop', '--port', port)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertEqual(sentinel.read_text(), 'client data')
            self.assertNotEqual(self.cli('status', '--port', port).returncode, 0)
        finally:
            self.cli('stop', '--port', port)

    def test_foreign_port_is_not_stopped(self):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            sock.listen(10)
            port = str(sock.getsockname()[1])
            self.assertNotEqual(self.cli('stop', '--port', port).returncode, 0)
            self.assertNotEqual(self.cli('start', '--port', port).returncode, 0)
            self.assertGreater(sock.fileno(), 0)

    def test_search_does_not_follow_junction_outside_root(self):
        ws = self.base / 'memory' / 'workspace'
        ws.mkdir(parents=True)
        outside = self.base / 'private'
        outside.mkdir()
        (outside / 'secret.txt').write_text('PRIVATE_MARKER_812')
        link = ws / 'linked'
        if os.name == 'nt':
            p = subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(outside)], capture_output=True)
            self.assertEqual(p.returncode, 0)
        else:
            link.symlink_to(outside, target_is_directory=True)
        try:
            rows = self.mcp([self.call('search_files', {'pattern': 'PRIVATE_MARKER_812'})])
            self.assertNotIn('PRIVATE_MARKER_812', rows[-1]['result']['content'][0]['text'])
        finally:
            if os.name == 'nt':
                os.rmdir(link)
            else:
                link.unlink()


if __name__ == '__main__':
    unittest.main()
