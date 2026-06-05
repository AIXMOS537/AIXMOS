import http.server
import json
import os
import subprocess
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).parent
MENTORSHIP = (ROOT / '..' / 'mentorship').resolve()
PORT = 8000

class OperatorDashboardHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/':
            self.path = '/dashboard/index.html'
            return http.server.SimpleHTTPRequestHandler.do_GET(self)
        if parsed.path.startswith('/api/'):
            return self.handle_api(parsed)
        return http.server.SimpleHTTPRequestHandler.do_GET(self)

    def handle_api(self, parsed):
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)
        if path == '/api/status':
            return self.respond_json({'status': 'ok', 'python': sys.executable})
        if path == '/api/list':
            return self.respond_text(self.run_cli(['--list']))
        if path == '/api/plan':
            return self.respond_text(self.run_cli(['--plan']))
        if path == '/api/prompt':
            name = query.get('name', ['master'])[0]
            return self.respond_text(self.run_cli(['--prompt', name]))
        if path == '/api/lesson':
            name = query.get('name', ['01-intro.md'])[0]
            return self.respond_text(self.run_cli(['--show', name]))
        if path == '/api/daily':
            return self.respond_text(self.run_cli(['--prompt', 'daily']))
        if path == '/api/codex':
            task = query.get('task', [''])[0]
            if not task:
                return self.respond_json({'error': 'task query required'}, status=400)
            return self.respond_text(self.run_cli(['--codex', task]))
        return self.respond_json({'error': 'unknown endpoint'}, status=404)

    def run_cli(self, args):
        cmd = [sys.executable, str(MENTORSHIP / 'cli.py')] + args
        proc = subprocess.run(cmd, cwd=str(MENTORSHIP), capture_output=True, text=True)
        if proc.returncode != 0:
            return proc.stderr or 'Error running CLI.'
        return proc.stdout

    def respond_json(self, data, status=200):
        payload = json.dumps(data)
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(payload.encode('utf-8'))))
        self.end_headers()
        self.wfile.write(payload.encode('utf-8'))

    def respond_text(self, payload, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.send_header('Content-Length', str(len(payload.encode('utf-8'))))
        self.end_headers()
        self.wfile.write(payload.encode('utf-8'))


def run_server():
    os.chdir(ROOT)
    with http.server.ThreadingHTTPServer(('127.0.0.1', PORT), OperatorDashboardHandler) as httpd:
        print(f'Operator dashboard is running at http://127.0.0.1:{PORT}')
        httpd.serve_forever()


if __name__ == '__main__':
    run_server()
