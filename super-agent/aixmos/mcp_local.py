"""Local newline-delimited JSON-RPC transport. No HTTP daemon or LLM required.

The client owns this process. Files and knowledge stay on this computer; tool
results sent to Claude/Cursor are subject to that client's data policy.
"""
import contextlib
import json
import sys
import time
from . import agent, settings

VERSION = '2.1.1'
PROTOCOLS = ('2025-11-25', '2025-06-18', '2025-03-26', '2024-11-05')
LOCAL_TOOLS = {'list_dir', 'read_file', 'search_files', 'write_file',
               'knowledge_search', 'recall', 'remember', 'run_command', 'run_python'}


class Session:
    def __init__(self, autonomy='safe', roots=None, allow_shell=False):
        self.ctx = agent.mcp_ctx(autonomy)
        if roots:
            self.ctx['roots'] = list(dict.fromkeys(self.ctx['roots'] + roots))
        self.allow_shell = allow_shell
        if allow_shell:      # --allow-shell at launch is the owner's once-per-session yes for code execution
            self.ctx['session_ok'] = {'run_command', 'run_python'}
        self.initialized = False

    def tools(self):
        out = []
        for item in agent.tool_schemas(self.ctx['autonomy']):
            t = item['function']
            name = t['name']
            if name not in LOCAL_TOOLS:
                continue
            if name in ('run_command', 'run_python') and not self.allow_shell:
                continue
            if name == 'remember' and self.ctx['autonomy'] == 'safe':
                continue
            out.append({'name': name, 'description': t['description'],
                        'inputSchema': t['parameters']})
        out.append({'name': 'aixmos_status', 'description': 'Local installation and tool permissions; no network access.',
                    'inputSchema': {'type': 'object', 'properties': {}}})
        return out

    def dispatch(self, message):
        mid = message.get('id') if isinstance(message, dict) else None
        def error(code, text):
            return {'jsonrpc': '2.0', 'id': mid, 'error': {'code': code, 'message': text}}
        if not isinstance(message, dict) or message.get('jsonrpc') != '2.0' or not isinstance(message.get('method'), str):
            return error(-32600, 'Invalid Request')
        method = message['method']
        if 'id' not in message:
            return None
        params = message.get('params', {})
        if not isinstance(params, dict):
            return error(-32602, 'params must be an object')
        if method == 'initialize':
            self.initialized = True
            proposed = params.get('protocolVersion')
            result = {'protocolVersion': proposed if proposed in PROTOCOLS else PROTOCOLS[0],
                      'capabilities': {'tools': {'listChanged': False}},
                      'serverInfo': {'name': 'aixmos-local', 'version': VERSION},
                      'instructions': 'Local AIXMOS tools. Inspect aixmos_status. Use only authorized folders. Shell, when enabled, has normal user privileges and is NOT an OS sandbox.'}
        elif method == 'ping':
            result = {}
        elif not self.initialized:
            return error(-32002, 'Initialize the session first')
        elif method == 'tools/list':
            result = {'tools': self.tools()}
        elif method == 'tools/call':
            name, args = params.get('name'), params.get('arguments', {})
            available = {t['name']: t for t in self.tools()}
            if not isinstance(name, str) or name not in available:
                return error(-32602, 'Unknown or disabled tool')
            if not isinstance(args, dict):
                return error(-32602, 'arguments must be an object')
            schema = available[name]['inputSchema']
            if any(k not in args for k in schema.get('required', [])):
                return error(-32602, 'Missing required argument')
            for key, value in args.items():
                typ = schema.get('properties', {}).get(key, {}).get('type')
                types = {'string': str, 'integer': int, 'number': (int, float), 'boolean': bool, 'array': list}
                if typ in types and (not isinstance(value, types[typ]) or (typ in ('integer', 'number') and isinstance(value, bool))):
                    return error(-32602, 'Invalid argument type: ' + key)
            if name == 'aixmos_status':
                text = json.dumps({'name': 'AIXMOS', 'version': VERSION, 'transport': 'stdio',
                                   'autonomy': self.ctx['autonomy'], 'roots': self.ctx['roots'],
                                   'shell_enabled': self.allow_shell, 'local_model_required': False})
            else:
                text = agent.call_tool(name, args, self.ctx)
            result = {'content': [{'type': 'text', 'text': text}], 'isError': text.startswith('ERROR')}
        else:
            return error(-32601, 'Method not found')
        return {'jsonrpc': '2.0', 'id': mid, 'result': result}


def serve(autonomy='safe', roots=None, allow_shell=False):
    session = Session(autonomy, roots, allow_shell)
    # stdout belongs exclusively to JSON-RPC, including while dependencies run.
    if hasattr(sys.stdin, 'reconfigure'):
        sys.stdin.reconfigure(encoding='utf-8')
        sys.stdout.reconfigure(encoding='utf-8')
    output = sys.stdout
    while True:
        line = sys.stdin.readline(1024 * 1024 + 1)
        if not line:
            break
        if len(line) > 1024 * 1024:
            print('MCP request exceeds 1 MiB', file=sys.stderr)
            return
        try:
            message = json.loads(line)
        except ValueError:
            reply = {'jsonrpc': '2.0', 'id': None, 'error': {'code': -32700, 'message': 'Parse error'}}
        else:
            with contextlib.redirect_stdout(sys.stderr):
                reply = session.dispatch(message)
        if reply is not None:
            output.write(json.dumps(reply, ensure_ascii=False) + '\n')
            output.flush()
