# AIXMOS Local Agent 2.1.1

2.1.1 removes every business-network feature: no network roles, operator certification, playbooks, prices,
console or private-repository setup. Installs from 2.1.0 or earlier are cleaned on upgrade.

A per-user local application with tools that Claude Code, Claude Desktop and
Cursor can launch directly. The stdio tool connection needs neither Ollama nor
a running web server. The browser chat and autonomous local-model loop need
Ollama and a downloaded model. Cloud clients may send tool results to their
providers: local execution does not mean cloud reasoning is offline.

## Windows installation

Run `AIXMOS-Local-Agent-2.1.1-Setup.exe`. The installer is unsigned. It installs
under `%LOCALAPPDATA%\AIXMOS` without requiring a system Python installation.
Choose Entrepreneur for a general client installation. Start AIXMOS opens the
local browser interface. Installation can optionally download Ollama and a model.

For a tools-only setup, from a terminal:

```powershell
.\AIXMOS-Local-Agent-2.1.1-Setup.exe --role builder --no-ollama --no-model --no-autostart
```

The client package contains application code, Python, media dependencies and
blank client data. It does not contain the owner's memory, keys, contacts,
business knowledge packs or business console. Add client-specific knowledge
through the app. The old full-bundle installer remains a separate artifact.

## Pair a client

In the installation folder, run `Pair Cursor.cmd`, `Pair Claude Code.cmd` or
`Pair Claude Desktop.cmd`. Restart the client, enable the AIXMOS server and
approve requested tools. The installer attempts Cursor and Claude Code pairing
when detected; config conflicts remain intact and are reported in install.log.
It also produces `aixmos-mcp.json` for manual import.

Pairing starts with read access to the AIXMOS workspace. For file creation and
editing, run this in the installation folder (substitute an existing folder):

```powershell
.\runtime\python.exe .\aixmos_local.py pair --client cursor --autonomy builder --root "C:\Client Projects" --replace
```

Use `--client claude-desktop` for Desktop, or `--client claude-code` for Code.
Claude Code manages its own registration; remove an existing `aixmos` entry
using Claude's MCP settings before changing it. `--replace` applies to JSON
configs only. Existing JSON configs are backed up before changes, unrelated
servers are preserved, and malformed configs are left untouched.

Add `--allow-shell` only when the client needs command/Python execution.
Commands run with the logged-in user's OS permissions. Allowed folders constrain
file tools and the command working directory; they are NOT an OS sandbox for
commands. Client tool approval should remain enabled. Direct paired tools do
not expose email sending, purchases, deployments or desktop clicking.

Try: “Use aixmos_status, then list my AIXMOS workspace.” In builder mode, try:
“Create a hello.txt file in the AIXMOS workspace and read it back to verify.”

## Lifecycle and upgrades

`Start AIXMOS.cmd`, `Stop AIXMOS.cmd`, and `Status AIXMOS.cmd` manage only this
installation. A busy port belonging to another app is reported, never killed.
Stop uses a local control token and checks installation identity and PID.
The web service logs to `memory/server.log`.

Stop the web service and close paired clients before upgrading. Re-run setup
in the same directory to preserve memory. A locked extraction now reports a
failure instead of silently claiming an upgrade succeeded. Extraction is not
transactional: keep the previous installer for recovery after a partial failure.

By default Windows setup attempts logon autostart; inspect install.log to confirm
registration. Stdio tools run on demand under the client's lifecycle and do not
need autostart. For removal, close the clients, stop AIXMOS, remove its MCP entries
and the AIXMOS-Server scheduled task, then archive memory before deleting the
installation. This release does not provide a one-click uninstaller.

## macOS and Linux

The accompanying mac-linux installer requires Python 3. It creates a venv and
installs requests and Pillow. After installation, use:

```bash
~/AIXMOS/.venv/bin/python ~/AIXMOS/aixmos_local.py pair --client cursor
~/AIXMOS/.venv/bin/python ~/AIXMOS/aixmos_local.py pair --client claude-code
~/AIXMOS/.venv/bin/python ~/AIXMOS/aixmos_local.py start --open
```

Install ffmpeg/whisper separately for media editing/transcription on Unix.
Windows is the tested platform for this release; macOS/Linux need native testing.

## Limits

No agent can guarantee every computer task. This release supplies local file,
knowledge, memory and optional shell/Python tools. Browser/desktop automation,
account access and application-specific connectors require additional integration.
The existing app also includes local chat, CRM, drafting and media workflows;
provider-dependent functions require the client's accounts and testing.
The legacy app's free public image provider remains enabled by its existing
setting; disable it in Integrations if prompts must stay local. Paired stdio
tools never invoke image providers. HTTP /mcp is retained as a legacy interface;
the new stdio path is the recommended local pairing method.

## Development

Run `python -m unittest discover -s tests -v` from the source directory.
Rebuild using `installer/build_local_installer.py --help`. The build requires a
verified base installer and a nonempty private owner-marker file, and scans
first-party payload text for common secret patterns and supplied personal markers.
This is a targeted gate, not a certification that arbitrary input is secret-free.

Pairing formats follow [Claude Code MCP](https://code.claude.com/docs/en/mcp),
[Cursor MCP](https://cursor.com/docs/mcp), and the
[MCP stdio specification](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports).
