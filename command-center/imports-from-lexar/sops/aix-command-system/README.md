# AIX AI Command System (portable)

Plug this folder into any Mac or PC, open in **Cursor**, add your keys to `.env`, and run.

## Mac — first time (2 minutes)

1. Plug in the flash drive and open this folder in **Cursor** (`File → Open Folder`).
2. Open the terminal in Cursor and run:

```bash
chmod +x scripts/*.sh
./scripts/setup-mac.sh
```

3. Edit `.env` with your Airtable token and base ID (see `.env.example`).
4. Test:

```bash
./scripts/aix list
./scripts/aix airtable list-templates
```

## Mac — every day

```bash
cd /Volumes/LEXAR/aix-command-system   # or your drive name
./scripts/aix run morning
./scripts/aix airtable get-table --table "Vehicles"
```

Or open the folder in Cursor and use the integrated terminal with `./scripts/aix ...`.

## Windows

```powershell
cd D:\aix-command-system
copy .env.example .env
# edit .env, then:
python aix_operator.py list
```

## Environment variables

| Variable | Used for |
|----------|----------|
| `AIRTABLE_API_KEY` | Personal access token from [airtable.com/create/tokens](https://airtable.com/create/tokens) |
| `AIRTABLE_BASE_ID` | `app...` from your base URL |
| `OPENAI_API_KEY` | Prompt `run` and `snapshot` |
| `SUPABASE_URL` / `SUPABASE_KEY` | Supabase fetch |
| `VERCEL_*` | Pass endpoints on the command line |

Full command reference: **IMPLEMENTATION.md**

## Security

- Never commit `.env` or paste tokens in chat.
- If a token was exposed, revoke it at Airtable and create a new one.
