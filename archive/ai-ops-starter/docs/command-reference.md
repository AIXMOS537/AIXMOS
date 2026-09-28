# Command Reference

**Brainiac 7** = Windows AI brain at `C:\AI-OPS-STARTER`. Hostname / Tailscale: `brainiac-7`.

## Windows — first run (one-liner)

See `README.md` WINDOWS FIRST COMMAND or:

```powershell
C:\AI-OPS-STARTER\scripts\phase1-windows-bootstrap.ps1
```

## Windows — daily

```powershell
cd C:\AI-OPS-STARTER
.\start-windows.ps1
```

```powershell
cd C:\AI-OPS-STARTER
docker compose down
```

```powershell
ollama list
ollama pull qwen2.5:7b
```

```powershell
cd C:\AI-OPS-STARTER
.\scripts\backup-windows.ps1
```

```powershell
cd C:\AI-OPS-STARTER
.\scripts\sync-nas-knowledge.ps1
```

## Mac — first run

```bash
cd ~/AI-OPS-STARTER && chmod +x *.sh scripts/*.sh && ./install-mac.sh
```

## Mac — sync flash

```bash
FLASH_DRIVE=/Volumes/AI-OPS ./start-mac.sh
```

```bash
./scripts/verify-flash-drive.sh /Volumes/AI-OPS/AI-OPS-STARTER
```

## Mac — remote access check

```bash
tailscale status
curl -s -o /dev/null -w "%{http_code}" http://100.x.y.z:3000
```

## Flash → Windows deploy

```powershell
robocopy E:\AI-OPS-STARTER C:\AI-OPS-STARTER /E /XD data /XF .env
cd C:\AI-OPS-STARTER
.\install-windows.ps1
```

## Docker

```powershell
docker compose ps
docker compose logs -f n8n
docker compose --profile optional up -d
```

## n8n test webhooks (after import + activate)

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:5678/webhook/team-question" -ContentType "application/json" -Body '{"question":"What is our PTO policy?"}'
```

Replace path with production webhook URL from n8n UI.
