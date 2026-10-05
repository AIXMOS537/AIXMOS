# AIXMOS memory

Learning is not training the model. AIXMOS remembers typed items with where they came from
(`super-agent/aixmos/memory_store.py`, ported from the private line; file `memory/aixmos-memory.db`).

## Kinds and who may write them

| Kind | Written by |
|---|---|
| USER_STATEMENT, PREFERENCE, DECISION, PROCEDURE | the owner (Command Center -> Memory) |
| VERIFIED_FACT | only the owner, or a passed verification (`promote(id, "verification:<check>")`) |
| MODEL_SUMMARY, INFERENCE | the agent (`remember` tool). A model can never create a fact. |
| SOURCE_DATA, EXTRACTED_FACT | imports |

The agent's `remember` tool always stores a model note. The owner turns a note into a fact with **Confirm**.
Notes from older versions (`agent_notes.json`) are imported once as model notes, never as facts.

## Scope

Every item is `LOCAL_ONLY` (default) or `CLOUD_OK`. `recall(..., for_cloud=True)` and `relevant(..., for_cloud=True)`
never return LOCAL_ONLY items, so private notes cannot reach a cloud model.

## Retrieval

`relevant(question)` ranks items by word overlap with the question, confirmed facts first, then the owner's own
statements. The agent's `recall` tool uses it, so it receives a few relevant items, not the whole store.

## Control

List, search, confirm and forget in the Command Center. `export(path)` writes everything as
`aixmos-memory/1` JSON. Forgetting blanks the text and hides the item.

## Not yet

Per-client separation for agencies running several businesses on one install, and memory from connectors (CRM,
mail) with their own provenance. Both are on the roadmap.
