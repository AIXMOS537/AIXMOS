---
name: tailscale-mesh
description: Tailscale mesh VPN that links the user's devices across any WiFi — the cross-network bridge for reaching the NAS/brain from anywhere. Load when syncing across networks or a device can't reach the NAS on its local LAN.
metadata:
  type: project
  domain: system
---

The cross-WiFi bridge for the home setup (the NAS and devices sit on different WiFi networks — see [[ugreen-nas]], [[device-architecture]]). Tailscale puts everything on one private mesh (100.x addresses) regardless of physical network.

## Tailnet state (2026-06-07, account AIXMOS537@)
- **Tablet** (`desktop-1it6el5`) = `100.64.0.1` — up.
- **Brainiac** (`brainiac-7`) = `100.64.0.1` — up; reachable from the tablet (ping OK). This is the cross-WiFi link that works no matter which WiFi each is on.
- `desktop-v9gqhhj` = `100.64.0.1` — offline (other Windows box).
- Tablet Tailscale was already authorized (cached login under AIXMOS537@) — `tailscale up` connected with no re-auth.

## Last gap for full roaming
- The **NAS is NOT on the tailnet yet** — it's only reachable on its local LAN (`192.168.1.236`, Verizon WiFi), which is why sync currently requires the tablet to be on that WiFi. **Fix: install/enable the Tailscale app in UGOS** (App Center → Tailscale → sign in as AIXMOS537). Then the NAS gets a 100.x address and every device reaches the brain from any WiFi (incl. SATTAR), no SMB-on-.59 needed.
- After that: point Brainiac's Obsidian at the NAS share (over Tailscale) → one live vault everywhere.
