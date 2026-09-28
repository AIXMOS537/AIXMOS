# `_models/` — bundled local model weights

This folder holds the GGUF model files that get copied from the USB to `~/.aixmos/models/` on first install.

**Why not bundle them in git?** Each model is 1-3 GB; together they're ~5 GB. They don't belong in version control. They live here on the USB drive only.

## Populating this folder

On a machine with internet:

```bash
bash _starter/download-models.sh
```

That script:
1. Runs `ollama pull` for every entry in `MANIFEST.json`
2. (Optional, not yet implemented) exports the pulled GGUF blobs from Ollama's store into this folder

For now the simpler distribution model is: the **customer's machine** runs `download-models.sh` once and pulls from `ollama.com`. Only when you want a truly air-gapped USB do you also export the blobs to this folder.

## What's in MANIFEST.json

| Tag | Size | Role |
|---|---|---|
| `llama3.2:3b` | 2.0 GB | default chat |
| `qwen2.5:1.5b` | 1.0 GB | fast fallback for weak machines |
| `phi3:mini` | 2.3 GB | reasoning / code |

Plus the custom `tmmt-brain` (built from llama3.2:3b + the Modelfile in `_brain/`).
