# Project AIXMOS - task list

## Phase 1 (2026-09-05) - JARVIS core: DONE
Theme + logo, toolchain, integrations panel, learning image generation, video generation,
prompt-driven video editing, email accounts + AI drafting, chat intents. Verified on this machine.

## Phase 2 (2026-09-11) - AI BUILDING KIT -> super agent: DONE
Kit: 24 AI Vault packs, 249 markdown files (PDF duplicates dropped), 1 dashboard HTML, 2 carousel JSON
templates. Copied to memory/kit and repurposed as follows (least -> most demanding):

- [x] 1. Vault: kit ingested into 1131 heading-aware passages, pure-Python BM25 search (1 ms),
       auto-cited in chat replies, /vault command, Packs browser (aixmos/knowledge.py)
- [x] 2. Prompt library: every blockquote prompt in the kit (252) searchable, "use in chat" / "give to agent"
- [x] 3. Skills: each pack is an activatable persona with [BRACKET] blanks filled from the business
       profile (18 fields); /skill <name> (aixmos/skills.py)
- [x] 4. Ops & CRM: leads (lead-sheet columns), 3-axis scoring via local model, appointments,
       revenue entries, follow-up sequences (cold outreach / missed call / no-show / review request)
       drafted by AI on due date, honest dashboard KPIs, 15-minute weekly review (aixmos/crm.py)
- [x] 5. Carousel generator: carousel-system copy rules + Pillow-rendered 1080x1350 slides in brand
       colours (aixmos/carousel.py) - verified end to end
- [x] 6. Super agent: tool loop on the local model (files, shell, python, web fetch/search, vault,
       notes, image/video, CRM, mail drafting, ask_user, finish) sandboxed to memory/workspace +
       allowed roots, three autonomy levels, kit doctrine (plan / small steps / proof / no fake data /
       human veto) (aixmos/agent.py) - verified: writes, verifies with shell + read, finishes
- [x] 7. External surfaces (aixmos/surfaces.py): OpenAI-compatible /v1/chat/completions (+stream) and
       /v1/models so any OpenAI-speaking app can use AIXMOS; MCP server at /mcp (initialize, tools/list,
       tools/call) so Claude Code / Cursor / any MCP client can drive the agent tools - verified
- [x] 8. UI: Super Agent, Vault & Skills, Ops & CRM panels; chat cards for agent runs and carousels;
       Integrations gained knowledge toggle, agent model / autonomy / allowed folders, endpoint info
- [~] 9. Cutover: the new build is bound on :8770 as standby; a Session-0 process from the previous
       build still answers until it is ended from an elevated shell or the machine reboots

## Phase 3 (2026-09-11) - one installable path for every client: DONE
- [x] Single artefact: dist/AIXMOS-4THEPEOPLE (Windows one-file exe via native stub; mac-linux installer;
       START-HERE; SHA256SUMS). PyInstaller AIXMOS-Setup.exe retired and removed from disk and the release.
- [x] Roles at install: TMMT Operator / AIXMOS Movement / Both; operator playbooks + console for TMMT;
       optional --tmmt-dev lane; MCP registration when Claude Code is present
- [x] Genesis first boot: mission, intake, capability showcase with live status, first build plan;
       mission context flows into chat and agent prompts
- [x] Mac parity in the app: whisper from PATH, OS fonts, bash for agent commands, running interpreter
- [x] Secret gate on every build; operator kit regenerated through the brain's gates
- [x] Verified: exe scratch install (role both, 1247 vault passages incl. TMMT kit, ffmpeg/whisper/Ollama
       online, Genesis + operator console served); mac scripts syntax-checked (not run on a Mac here)
- [ ] Owner follow-ups: TMMT-TEAM-DRIVE\windows\bootstrap.ps1 still clones the decoy Metavibez4L/TMMT;
       run the mac installer once on the M1 to confirm end to end

Ops notes: qwen7b-max as the agent model crashed Ollama on this 2-core machine; the agent defaults
to qwen2.5:3b (7B stays opt-in under Integrations). Agent steps take ~30-60 s each here.
Not verifiable without keys/accounts: paid image/video providers, live email sending, OAuth sign-in.
