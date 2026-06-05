# TMMT Airtable base

Parsed from your link:

```
https://airtable.com/appcenWUju039rD7b/tbl4gndUYeiOUWYRR/viwuJ5HJDh6RoplEb
```

| Field | Value |
|-------|--------|
| Base ID | `appcenWUju039rD7b` |
| Table ID | `tbl4gndUYeiOUWYRR` |
| View ID | `viwuJ5HJDh6RoplEb` |

## What is configured

- `.env` → `AIRTABLE_BASE_ID=appXXXXXXXXXXXXXX`
- `config/tmmt_integration.json` → same base + primary table ID in `snapshot_tables`

## What you still need

1. **Airtable personal access token** — [airtable.com/create/tokens](https://airtable.com/create/tokens) scoped to base `appcenWUju039rD7b`
2. Add to `.env`: `AIRTABLE_API_KEY=pat…` (never commit)

## Test commands

```bash
cd /Volumes/LEXAR/AIX_AI_COMMAND_SYSTEM
source scripts/load-env.sh

# List real table names in your base (after API key is set)
./scripts/aix integrate discover-airtable

# Integration status (+ probe tables when keys exist)
./scripts/aix integrate status --probe

# Fetch the table you linked (ID or name works)
./scripts/aix airtable get-table --table tbl4gndUYeiOUWYRR
```

After `discover-airtable`, update `airtable.snapshot_tables` in `config/tmmt_integration.json` to match real names and remove any that 404.

## Do not run on live base

```bash
# Do NOT run unless you intend to create new tables from CSV templates
./scripts/aix airtable sync-templates
```
