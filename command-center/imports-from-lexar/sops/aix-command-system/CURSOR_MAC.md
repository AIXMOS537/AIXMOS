# Continue in Cursor on MacBook

## 1. Open the project

1. Plug in the flash drive.
2. Open **Cursor**.
3. **File → Open Folder…**
4. Choose:
   - `/Volumes/LEXAR/aix-command-system`  
   (Replace `LEXAR` with your drive name if different — check Finder → Locations.)

## 2. One-time setup (terminal in Cursor)

Press **Ctrl+`** ` or **View → Terminal**, then:

```bash
chmod +x scripts/*.sh
./scripts/setup-mac.sh
```

## 3. Add your API keys

1. Open `.env` in the editor (created by setup, or copy from `.env.example`).
2. Set at minimum:

```env
AIRTABLE_API_KEY=pat_your_token
AIRTABLE_BASE_ID=app_your_base_id
OPENAI_API_KEY=sk-optional_for_prompts
```

3. Save the file. **Do not commit `.env`.**

### Load keys in the terminal

**Option A** — use the wrapper (recommended):

```bash
./scripts/aix list
```

**Option B** — install the **Dotenv** extension in Cursor, then open a **new** terminal.

**Option C** — manual:

```bash
set -a && source .env && set +a
python3 aix_operator.py list
```

## 4. Run & debug in Cursor

- **Terminal:** `./scripts/aix <command>`
- **Debug:** **Run and Debug** (sidebar) → pick **“AIX: list prompts”** or **“AIX: airtable list-templates”** (uses `.env` via `launch.json`)

## 5. Common commands

```bash
./scripts/aix list
./scripts/aix show morning
./scripts/aix run morning
./scripts/aix airtable list-templates
./scripts/aix airtable import-template --template Bills
./scripts/aix airtable get-table --table "Vehicles"
./scripts/aix snapshot --airtable-tables "Vehicles,Bookings" --prompt-name tmmt_command_center_snapshot
```

## 6. Sync changes back to the flash drive (optional)

Work in `~/projects/aix-command-system` on the Mac, then copy back to the drive when done. Or keep working directly on `/Volumes/LEXAR/aix-command-system` so the flash drive is always current.

## 7. Python on Mac

If `python3` is missing:

```bash
brew install python
```

Or download from [python.org](https://www.python.org/downloads/).

## 8. Recommended Cursor extensions

- **Python** (Microsoft) — run/debug
- **Dotenv** (mikestead) — auto-load `.env` in terminal

No `pip install` required — the CLI uses only the Python standard library.
