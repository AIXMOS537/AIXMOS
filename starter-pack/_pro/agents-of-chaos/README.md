# Agents of Chaos — PRO pack (LOCKED in v1)

The 10 named-persona agents (moose, chummo, jarvis, vision, captain, wonderwoman, flyguy, bob, sticks, tank) from `AIXMOS-AGENTS` are NOT installed in the v1 starter pack.

**Why locked?** They add 7 named-persona models, each with its own port + system prompt + tools. For a first-time user on an old 8 GB laptop, this is too many things to wire up and too many things to break. The lean v1 ships one agent (tmmt-brain) so the customer gets value in 3 minutes instead of 30.

## Unlocking

To enable on this machine after v1 is working:

```bash
bash _pro/unlock.sh        # Mac
powershell _pro/unlock.ps1 # Win
```

The unlock script:
1. Verifies all 3 v1 models are present and the user has had a successful chat session
2. Installs the AoC code from `_pro/agents-of-chaos/agents/`
3. Spins up agent-server on `:7777` (mirrors BRAINIAC's port)
4. Adds menu entries 11-20 to LAUNCH for each agent

**Status:** unlock script + AoC source not yet bundled. Will land in v1.2.
