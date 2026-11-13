# GPT Workbench

Central repository for the GPT Workbench project.

## Repository structure

- `docs/` — operating protocol, integration status, quick start, quality controls and current state.
- `docs/AUTORED_IDEA_*` — architecture, roadmap, security/DR, tests, decisions, audits, deployment log and project state.
- `autored/` — provider-neutral deterministic workflow core.
- `cloudflare/` — Worker runtime and versioned D1 migrations.
- `scripts/` — local TTS/FFmpeg renderer, RSS source audit, safe Publora API client, compliance-gated media scheduling and read-only provider preflight.
- `requirements-render.txt` — pinned free renderer dependency.
- `wrangler.toml` — Cloudflare Worker, D1, AI and Cron configuration.
- `templates/` — reusable project, state, task, decision and error templates.
- `tests/` — deterministic unit, documentation and safety regression tests.

## Source of truth by system

- **Notion:** operational knowledge, decisions, pages and tasks.
- **ChatGPT Library:** working file archive and source copies under `/Assistant_Workbench/`.
- **GitHub:** version-controlled documentation, code and CI.
- **Cloudflare:** deployed Worker and D1 operational backend.
- **Dropbox:** optional secondary file destination; upload has not yet been verified.

## Operating rules

- Preserve originals; do not silently overwrite or delete.
- Verify writes by reading files back.
- Never commit passwords, API keys, access tokens, or personal data.
- Do not claim cross-service synchronization unless each transfer is confirmed.
- Keep AUTORED IDEA's design, implementation, tests and operational state documented together.
- Never mark an integration as production-ready without an end-to-end test and independent confirmation.

## Start here

### AUTORED IDEA

1. [Project state](docs/AUTORED_IDEA_STATE_PL.md)
2. [Project architecture](docs/AUTORED_IDEA_ARCHITECTURE_PL.md)
3. [Execution roadmap](docs/AUTORED_IDEA_EXECUTION_PLAN_PL.md)
4. [Architecture decisions](docs/AUTORED_IDEA_DECISIONS_PL.md)
5. [Security and Disaster Recovery](docs/AUTORED_IDEA_SECURITY_DR_PL.md)
6. [Test plan and acceptance criteria](docs/AUTORED_IDEA_TEST_PLAN_PL.md)
7. [Deployment log](docs/AUTORED_IDEA_DEPLOYMENT_2026-11-13_PL.md)
8. [Media renderer and TTS](docs/AUTORED_IDEA_RENDERER_PL.md)
9. [Provider connection and quota audit](docs/AUTORED_IDEA_PROVIDER_AUDIT_2026-11-13_PL.md)
10. [Verified baseline audit](docs/AUTORED_IDEA_AUDIT_2026-11-13_PL.md)
11. [Publora integration setup](docs/AUTORED_IDEA_PUBLISH_SETUP_PL.md)
12. [Core package](autored/README.md)

### GPT Workbench

1. Read [quick start](docs/QUICK_START_PL.md).
2. Read [current state](docs/WORKBENCH_STATE.md).
3. Read [integration status](docs/INTEGRATION_STATUS.md).
4. Follow [operating protocol](docs/OPERATING_PROTOCOL.md).
