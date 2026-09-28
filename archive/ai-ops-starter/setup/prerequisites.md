# Prerequisites

## Windows 11 Pro (AI brain)

| Tool | Install |
|------|---------|
| Docker Desktop | https://docs.docker.com/desktop/setup/install/windows-install/ |
| Ollama | https://ollama.com/download/windows |
| Tailscale | https://tailscale.com/download/windows |
| Git (optional) | https://git-scm.com/download/win |

**Hardware:** 16 GB+ RAM recommended for `qwen2.5:7b`; NVIDIA GPU optional (Ollama uses it if present).

## MacBook (admin)

| Tool | Install |
|------|---------|
| Tailscale | `brew install --cask tailscale` |
| rsync | built-in |
| Git | `xcode-select --install` or Homebrew |

Docker on Mac is **optional** (testing only).

## UGREEN NAS

- Enable SMB
- Create share `AI-OPS`
- Dedicated user `ai-ops` with least privilege

## Flash drive

- 8 GB+ exFAT
- Label `AI-OPS` for Mac sync scripts

## Network

- No port forwarding to AI services
- Tailscale on Windows + Mac for remote UI access
