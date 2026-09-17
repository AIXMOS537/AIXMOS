# AIXMOS AGENT NETWORK — INSTALL

Ten agents on your own machine. Runs fully offline if you want it to.
**For the people. By the people.**

---

## WHAT YOU GET

| Agent | Does |
|---|---|
| **CHUMMO** | general reasoning / orchestrator front door |
| **MOOSE** | takes a plan and executes it |
| **CAPTAIN** | dispatch and coordination |
| **WONDER WOMAN** | research and verification |
| **VISION** | reads images, screenshots, documents |
| **JARVIS** | infrastructure checks |
| **TANK** | container / hub-brain control |
| **FLY GUY** | fast small jobs |
| **BOB** | builder |
| **STICKS** | overdue scan and reminders |

Plus a scheduler, a contacts tool, and an **iMessage relay** (macOS only).

---

## START HERE — one file

**Double-click `AIXMOS.command`** (Mac) or **`AIXMOS.bat`** (Windows).

That is the whole thing. It checks what is actually true on this machine — node, a thinking
backend, whether anything is able to send messages — tells you honestly, and then offers a
menu: talk to an agent, install, set up offline mode, run the safety tests, manage the
do-not-contact list.

> This folder contains 25 older entry points (`START-HERE`, `RUN-FROM-USB`, `AI-BRAIN`,
> `LOAD-ME-FIRST`, `MAKE-DESKTOP-BRAIN` …). They still work and are kept for the USB and
> flashdrive flows, but **you do not need to choose between them any more.** The launcher
> is the door.

From a terminal:

```bash
bash bin/aixmos            # the menu
bash bin/aixmos doctor     # preflight only — exits non-zero if not runnable
bash bin/aixmos vision     # run one agent directly
```

`doctor` is safe to put in a script or a cron: it exits `1` when the machine is not in a
state to run, including when the do-not-contact list is unreadable.

Installing (menu option 2, or `bash install-mac.sh`) mirrors the tree to `~/AIXMOS` and
creates one alias per agent, so `chummo`, `moose`, `vision` … work from any terminal.

---

## PICK HOW IT THINKS

Set `AIXMOS_LLM_BACKEND` in `config/aixmos.env`:

| Value | Needs | Good for |
|---|---|---|
| `ollama` | [Ollama](https://ollama.com) + one model pulled | **fully offline. No API key. No data leaves your machine.** |
| `claude` | `ANTHROPIC_API_KEY` | strongest reasoning |
| `auto` | either | Claude when online, Ollama when not |

Offline on a laptop or USB: `OLLAMA_MODEL=phi3:mini` (~2.3 GB).

**You need nothing else to start.** Supabase, GHL and TMMT OS keys in the example config are
only for STICKS' overdue scan — leave them blank and every other agent still works.

---

## MESSAGING — READ THIS PART

### It will not send anything until you turn it on
`imessage-relay/config.example.json` ships with **`allow_send: false`**, `safe_mode: true`,
empty allowlists, and hourly rate caps. Copy it to `config.json` and change what you want.
Nothing sends on a default install.

### The do-not-contact gate is on and cannot be bypassed
Every outbound path — GHL, Quo, iMessage — goes through one function, and that function
checks a local suppression list at `~/.aixmos/do-not-contact.json` first.

- Someone replies **STOP / UNSUBSCRIBE / CANCEL / QUIT** → suppressed immediately, before
  any other check runs.
- **START** puts them back.
- Free text like *"stop texting me"* is **held for a human**. It is not auto-suppressed,
  because guessing wrong in either direction is bad.
- **It fails closed.** If the list is unreadable, the send is refused rather than assumed
  safe.
- A dry run to a suppressed number is refused too — a dry run that says "would send" is a
  line that gets copied into a real one.

Manage it by hand:
```bash
npm run dnc            # where the list lives
node -e "console.log(require('./lib/suppression').suppress('555-123-4567','manual'))"
```

Run `npm test` any time — 28 tests, no dependencies, and they cover the gate.

### Two things that are your call, and should be

1. **iMessage sending needs macOS + Full Disk Access for your terminal.** That is a real
   privilege: it reads your message database. Grant it only if you want the relay, and only
   on a machine you own. Everything else in the pack works without it.
2. **Telegram needs your own bot.** Talk to `@BotFather`, make a bot, put the token in your
   config. Do not reuse anyone else's token.

**Messaging people costs money and carries rules.** In the US that means TCPA and, for
anything debt-related, FDCPA. The gate above helps you honour an opt-out; it does not make
you compliant on its own. Know the rules for what you are sending.

---

## WHAT IS NOT IN HERE

- **No credentials.** Every key in `config/aixmos.env.example` is a blank you fill in.
  Nothing phones home to anyone else's account.
- **No customer data.** No contacts, no lists, no CRM records ship with this.
- **`agents/rick.js` is owner-tier and is excluded by both installers.** It targets one
  specific operation's Slack, Vercel projects and operator list. It refuses to run without
  `AIXMOS_OWNER_TIER=1` and is not one of the ten agents.

---

## IF SOMETHING BREAKS

```bash
npm test                  # the safety gate
node test-all-agents.js   # smoke every agent
aixmos-tests              # same, after install, live
```

Offline mode not working? Check Ollama is up: `curl http://localhost:11434/api/tags`
