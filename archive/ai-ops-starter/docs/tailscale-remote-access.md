# Tailscale Remote Access

## Goals

- MacBook admin accesses **Brainiac 7** (Windows AI stack) **without** public port exposure
- All Docker ports stay on `127.0.0.1` on Windows
- Tailscale provides encrypted peer-to-peer (or relay) connectivity

---

## Install

1. **Brainiac 7 (Windows):** https://tailscale.com/download/windows
2. **MacBook:** https://tailscale.com/download/mac
3. Same tailnet (same login/org)

---

## Windows (Brainiac 7)

Rename PC hostname to `brainiac-7` (optional but recommended for MagicDNS).

```powershell
tailscale up
tailscale status
tailscale ip -4
```

Note the IPv4 (e.g. `100.x.y.z`).

Enable **MagicDNS** in Tailscale admin → access:

- Open WebUI: `http://brainiac-7:3000`
- n8n: `http://brainiac-7:5678`

Set in `.env`:

```
TAILSCALE_WINDOWS_HOST=brainiac-7
```

---

## Mac

```bash
tailscale up
tailscale status
ping brainiac-7   # if MagicDNS enabled
```

Access:

- Open WebUI: `http://brainiac-7:3000` or `http://100.x.y.z:3000`
- n8n: `http://brainiac-7:5678`

---

## Firewall (Windows)

Allow inbound **only** on Tailscale adapter for ports 3000, 5678 if needed, OR use Tailscale serve/funnel (not enabled in this kit).

**Recommended:** Tailscale ACL restricting ports 3000/5678 to your Mac user/device tags.

Example ACL snippet (admin console):

```json
{
  "action": "accept",
  "src": ["group:admins"],
  "dst": ["tag:brainiac-7:3000", "tag:brainiac-7:5678"]
}
```

Tag Windows machine `tag:brainiac-7` in Tailscale device settings (or keep `tag:windows-ai` if already deployed — update ACL to match).

---

## Security notes

- Do not use Funnel/public serve for WebUI/n8n
- MFA on Tailscale identity provider
- Review `tailscale status` monthly for unknown devices

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Timeout from Mac | Both devices `tailscale status` online |
| Works on LAN IP not Tailscale | Use Tailscale IP or `brainiac-7` MagicDNS |
| WebUI loads, n8n doesn't | Check n8n basic auth; port 5678 in ACL |

See `troubleshooting.md` and `docs/brainiac-7.md`.
