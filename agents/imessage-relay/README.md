# Work-iPhone (iMessage) relay — Mac setup

This runs on your **M1 Max Mac** (the one signed into the work iPhone's Apple ID /
iMessage). It lets the Brain on BRAINIAC-7 send texts "from the iPhone" by driving
Messages.app. They talk over Tailscale.

## One-time setup on the Mac

1. **Copy this folder** (`imessage-relay/`) to the Mac, e.g. `~/imessage-relay`.
2. Make sure Node is installed: `node -v` (if missing: `brew install node`).
3. **Pick a secret** (any random string) — it must match `IMESSAGE_RELAY_SECRET`
   on the Windows side.
4. Start it:
   ```bash
   RELAY_SECRET='choose-a-long-random-secret' node ~/imessage-relay/relay.js
   ```
5. macOS will pop up **"Terminal/node wants to control Messages"** → click **OK**.
   (If you miss it: System Settings → Privacy & Security → Automation → enable
   Messages for Terminal.)
6. Test locally on the Mac:
   ```bash
   curl -s localhost:8787/health
   curl -s -X POST localhost:8787/send -H 'X-Relay-Secret: choose-a-long-random-secret' \
     -H 'Content-Type: application/json' -d '{"to":"+1YOURCELL","text":"relay test"}'
   ```

## Point the Brain at it (on BRAINIAC-7)

In `AIXMOS-AGENTS/.env`, uncomment + set (the Mac's Tailscale IP is `100.64.0.1`):
```
IMESSAGE_RELAY_URL=http://100.64.0.1:8787
IMESSAGE_RELAY_SECRET=choose-a-long-random-secret
```
Then `node send-sms.js --status` should show **imessage [READY]**, and
`node send-sms.js --to +1YOURCELL --text "hi" --channel imessage` will route through it.

## Keep it running (autostart)

Use a `launchd` agent so it survives reboots — `loginwindow`/`KeepAlive`. Drop a
plist in `~/Library/LaunchAgents/com.tmmt.imessage-relay.plist` that runs
`relay.js` with `RELAY_SECRET` in `EnvironmentVariables`, then
`launchctl load` it. (Ask the Brain to generate the plist when you're on the Mac.)

## Caveats (be honest about these)

- **iMessage (blue)** works whenever the Mac is awake + signed in.
- **SMS (green)** to non-iMessage phones only works if the **iPhone is nearby /
  on the same Apple ID with Text Message Forwarding ON**. If the iPhone is away,
  green-number sends fail — the Brain will fall back to GHL automatically.
- The Mac must be **awake** (not just plugged in). Disable App Nap / set
  "prevent sleeping" for reliability.
- Keep the relay **behind Tailscale only** — never expose port 8787 to the public
  internet. The shared secret is a second lock, not the only one.
