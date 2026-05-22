# Brainiac Tier Environment Templates

Copy the tier matching this machine, then run `scripts/provision-brainiac-node.ps1` (recommended).

| File | Tier | Use |
|------|------|-----|
| `brainiac-7.env.example` | 7 | Owner supreme PC |
| `brainiac-6.env.example` | 6 | Second HQ / regional brain |
| `brainiac-5.env.example` | 5 | Branch site brain |
| `brainiac-4.env.example` | 4 | Lead operator workstation |
| `brainiac-3.env.example` | 3 | Field operator laptop |
| `brainiac-2.env.example` | 2 | Thin client (remote WebUI) |
| `brainiac-1.env.example` | 1 | Pocket / flash-only access |

All tiers set `BRAINIAC_UPSTREAM_HOST=brainiac-7` unless tier is 7.
