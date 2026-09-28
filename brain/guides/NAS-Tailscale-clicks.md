# ⭐ Put the NAS on Tailscale — click-by-click
_The one step that makes your brain sync from ANY WiFi. ~2 minutes. See [[tailscale-mesh]], [[ugreen-nas]]._

**Why:** right now the brain only syncs when a device is on the NAS's home WiFi (Verizon, `192.168.1.x`). Tailscale gives the NAS a private address that works on every network — so the tablet, Brainiac, and the Macs reach the brain no matter which WiFi they're on, and you never enable SMB on the second interface.

## Do this on the NAS
1. On any computer, open **http://192.168.1.236:9999** and log in to the NAS (UGOS).
2. Open the **App Center** (the apps/store icon).
3. Search **Tailscale** → **Install**.
4. Open Tailscale → **Sign in** → use the **`AIXMOS537`** account (same one the tablet + Brainiac use). Approve the login in the browser if asked.
5. When it shows **Connected**, note the NAS's Tailscale address (a `100.x.x.x` number) — or its Tailscale name.

## Then tell me
Send me the NAS's **Tailscale 100.x address** (or name). I'll:
- Add a second git remote so the tablet syncs over Tailscale from any WiFi (not just Verizon)
- Update `sync-brain.ps1` to use it
- Finish **Brainiac** + the **Macs** (they're already on the tailnet) so all devices share the one live brain

## If you can't find Tailscale in App Center
Some UGOS versions hide it — tell me and I'll give you the Docker-based install steps instead.
