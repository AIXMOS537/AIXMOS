# AIXMOS — Put It Where Every Device Can Reach It

**Recommended home: a PRIVATE GitHub repo** (you already have GitHub: `AIXMOS537`).
Why this and not a shared drive: every OS clones it (both Windows PCs, both Macs), your
iPhones view it in the GitHub app, it's **versioned so you can roll back**, it's **free**,
and **AIXMOS Engine on any machine can clone and deploy straight from it.**

> Split that keeps things clean: **code → GitHub**, **data/photos → NAS**. The *running*
> Gateway is already reachable by every device once deployed — this is just the source kit's home.

**Safe:** this folder has **no secrets** — `deploy.sh` asks for them at deploy time and
`.gitignore` keeps local config out of git. Just keep the repo **Private**.
*(It's already a git repo with an initial commit — you only need to push it.)*

---

## Option A — Let AIXMOS Engine publish it (easiest)
Open AIXMOS Engine in this folder and paste:

> Create a new PRIVATE GitHub repo named aixmos-gateway under my account and push this
> folder to it. It's already a git repo with a commit. Confirm the repo URL and that it's private.

## Option B — Do it yourself (3 commands)
1. On github.com, create an empty **Private** repo named `aixmos-gateway` (don't add a README/license).
2. In this folder, in Terminal (Mac) or Git Bash (Windows):
```bash
git remote add origin https://github.com/AIXMOS537/aixmos-gateway.git
git branch -M main
git push -u origin main
```

---

## Reach it from every device (after it's pushed)
- **Any Mac / PC:** `git clone https://github.com/AIXMOS537/aixmos-gateway.git` → deploy or update with `git pull`.
- **iPhones:** the **GitHub app** to view/read; or the **Working Copy** app to clone and edit on the phone.
- **Deploy once:** on whichever machine, `cd aixmos-gateway` and follow `HANDOFF.md` / `README.md`.

## Keep it current (one source of truth)
Edit on any machine, then:
```bash
git add -A && git commit -m "what changed" && git push
```
Every other device: `git pull`. The repo is the single, always-reachable home.

## Optional — owned mirror on the NAS
Also copy this folder to `TMMT/AIXMOS/aixmos-gateway` on the NAS. Over Tailscale it's reachable
from all devices and gives you a private backup you fully own. Git stays primary; the NAS copy is belt-and-suspenders.
