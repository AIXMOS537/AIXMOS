# AIXMOSXTMMT-OPS (Portable)

Flash-drive ops stack for **macOS** and **Windows**: n8n, Supabase clock app, Level A autonomy config.

## One-time per computer

Install:

- [Node 20+](https://nodejs.org)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Ollama](https://ollama.com)
- [Tailscale](https://tailscale.com) (optional, for `prime` / NAS)

```bash
ollama pull qwen2.5-coder:14b
ollama pull llama3.2:3b
ollama pull nomic-embed-text
```

Keep models in `~/.ollama/models` — **not** on the USB stick.

## Mac quick start

```bash
cd /Volumes/YOURUSB/AIXMOSXTMMT-OPS
chmod +x scripts/setup-mac.sh
./scripts/setup-mac.sh
# edit .env
npm run doctor
npm run start          # n8n → http://localhost:5678
npm run clock:install
npm run clock:dev      # http://localhost:5173
```

## Windows quick start

```powershell
cd E:\AIXMOSXTMMT-OPS
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup-windows.ps1
# edit .env
npm run doctor
npm run start
npm run clock:install
npm run clock:dev
```

## Supabase

1. Create project at [supabase.com](https://supabase.com)
2. Run `sql/001_supabase_empire.sql` in SQL Editor
3. After Auth setup, run `sql/002_rls_clock.sql`
4. Copy URL + keys into `.env`

## NAS sync (UGREEN DH2300)

When NAS is mounted:

```bash
npm run sync-nas
```

Sets `NAS_AI_PATH_MAC` or `NAS_AI_PATH_WIN` in `.env` first.

## Security

- Encrypt the USB drive
- Never commit `.env`
- Rotate keys if USB is lost

## Claude Code

```text
Read EMPIRE-OPS-SPEC.md. Execute PHASE P0, then P1…
```
