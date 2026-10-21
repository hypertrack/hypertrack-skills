# AGENTS.md

Agent skill repository for HyperTrack integration. Read `VISION.md` before changing the skill.

## Repository structure

```
hypertrack-skills/
├── skills/
│   └── hypertrack-integration/
│       ├── SKILL.md             # Model, rules, workflow, where to fetch each docs page, judgment the docs lack, go-live checklist
│       └── references/
│           └── testing.md       # Agent-side checks (curl, signature), device test, traps, symptoms
├── tools/
│   └── check_refs.py            # URLs resolve; API endpoints exist in the live OpenAPI spec
├── justfile                     # check, budget, refs, fmt
├── README.md, AGENTS.md, VISION.md, TODO.md
└── package.json                 # Pi package manifest (pi.skills)
```

`skills/hypertrack-integration/` is what ships to users. `tools/` doesn't ship.

## How the skill works

The skill routes; the docs are the source. `SKILL.md` gives the agent a short model and the rules agents get wrong. For each task it gives an explicit instruction to fetch one docs page (`https://hypertrack.com/docs/<slug>.md`, `https://hypertrack.com/reference/webhooks/<event>.md`, the OpenAPI spec, an SDK reference, or a quickstart). It adds one line each for judgment the docs don't contain. `references/testing.md` covers verification, which the docs don't.

## Editing guidelines

- **Don't restate the docs.** Before adding a line, check whether one docs page covers it. If it does, link that page with an explicit fetch instruction and add nothing else. Only judgment the docs lack (decisions, rules agents get wrong, traps scattered across pages) goes in, one line each with a link.
- **Docs are wrong? Fix the docs.** Open a PR in `hypertrack/hypertrack-content` instead of patching around it in the skill. A temporary one-liner is fine until the fix ships, with a TODO to remove it.
- **Verify before writing.** Every claim must come from a source you read in that session: a docs page, the OpenAPI spec, an SDK reference or changelog, or the SDK source. Label platform knowledge that isn't from HyperTrack's sources as such, or leave it out.
- **Size:** `SKILL.md` ≤ 200 lines and all skill Markdown ≤ 300, enforced by `just budget` (part of `just check`). Raising the limit is a deliberate decision in its own commit.
- **Cut by content, not by file.** When trimming, ask of each line whether a docs page covers it and whether it's judgment.
- Placeholders are explicit (`<test-worker>`, `<order_handle>`). Credentials in examples come from environment variables.
- Run `just check` before committing (size, formatting, links, API endpoints).
- When the skill's file structure changes, also update the Agent Skills docs page in `hypertrack/hypertrack-content` (`docs/content/guides/agent-skills.mdx`), which shows the tree.

## Distribution

- **skills CLI:** `npx skills add hypertrack/hypertrack-skills` (Claude Code, Codex, Cursor, Pi, and other Agent Skills agents)
- **Pi package:** `pi install git:github.com/hypertrack/hypertrack-skills` (uses the `pi.skills` manifest in `package.json`)
- **Manual:** copy or symlink `skills/hypertrack-integration/` into the agent's skills directory
