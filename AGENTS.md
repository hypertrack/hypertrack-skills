# AGENTS.md

Agent skill repository for HyperTrack integration.

## Repository structure

```
hypertrack-skills/
├── skills/
│   └── hypertrack-integration/
│       ├── SKILL.md                 # Entry: mental model, rules, workflow, sources of truth
│       ├── references/
│       │   ├── mobile.md            # Shared mobile rules: worker handle, permissions, errors, clock-in, on-device orders
│       │   ├── ios.md               # iOS setup + compiled Swift snippets
│       │   ├── android.md           # Android setup + compiled Kotlin snippets
│       │   ├── cross-platform.md    # React Native, Expo, Flutter, Ionic Capacitor, .NET MAUI
│       │   ├── backend.md           # Auth, errors, orders lifecycle, places, workers, nearby, embeds
│       │   ├── webhooks.md          # Delivery contract, HMAC-SHA1 verification, event map
│       │   ├── testing.md           # Agent verification, device test protocol, traps, symptoms, outages
│       │   └── production.md        # Secrets, store review, whitelisting, outage follow-up, go-live checklist
│       └── scripts/
│           ├── ht.py                # Verification CLI (check, worker, track, order, webhooks, complete/cancel, sign)
│           └── audit_mobile.py      # Static audit of a mobile repo's HyperTrack setup
├── tools/
│   ├── check_refs.py                # URLs resolve; API endpoints exist in the live OpenAPI spec
│   └── check_snippets.py            # Compile Swift/Kotlin/TS/Dart/C# snippets against the latest SDK releases
├── tests/                           # Regression tests: ht.py (mock API), audit_mobile.py (fixtures), tools, snippet behavior
├── justfile                         # check, test, refs, snippets, fmt, scripts
├── README.md, AGENTS.md, VISION.md, TODO.md
└── package.json                     # Pi package manifest (pi.skills)
```

`skills/hypertrack-integration/` is what ships to users. `tools/` and `.cache/` never ship.

## How the skill works

1. `SKILL.md` gives the agent the model (workers, orders, places, tracking intent), the rules that must hold, and a workflow: inspect the repo, settle decisions, implement, verify, go live.
2. References load on demand per task. Each owns one area; they cross-link instead of repeating each other.
3. Facts that change (field lists, payloads, SDK symbols) are kept minimal and point to sources of truth: the OpenAPI spec (`https://hypertrack.com/reference/openapi.yaml`), the docs `.md` versions (`https://hypertrack.com/docs/llms.txt`), and the SDK references and quickstarts. The skill holds the judgment the docs don't: decisions, invariants, traps, and verification.
4. `scripts/` give agents deterministic checks: `audit_mobile.py` for static mobile config and `ht.py` for live account and webhook verification.

## Key domain concepts

- Backend-managed **Orders** drive tracking by default. On-device orders (native iOS 5.12+/Android 7.12+) are for offline-first apps only. `isTracking` / `work_status` are low-level.
- `track_mode`: `pre_shift`, `on_shift`, `full_shift` (`on_time` and `flex` are deprecated).
- GeoJSON (API, webhooks) is `[longitude, latitude]`; every SDK location type is latitude, then longitude (Swift labels, Kotlin/C#/Dart positional, JS `{latitude, longitude}`).
- Silent push (APNs + FCM, keys uploaded to the dashboard) is mandatory for remote start and stop.
- `worker_handle` is set on login and launch and cleared to `""` on logout.
- SecretKey is server-only. Webhooks are signed with HMAC-SHA1 of the raw body using the SecretKey.
- Server-side availability (`work_status.available`) does not propagate to the device. Set availability on the device.

## Editing guidelines

- **Verify before writing.** Every API field and endpoint must exist in the OpenAPI spec. Every SDK symbol must match the SDK reference or a quickstart. Don't copy from the docs blindly; they have had compile errors.
- **Snippets compile.** `swift`, `kotlin`, `ts`, `dart`, and `csharp` fences must be complete compilable units (imports + declarations; no top-level statements in Kotlin). Run `just snippets` after touching them. Use fence info `no-check` only for intentionally partial code. Gradle Kotlin DSL goes in `kts` fences, not `kotlin`.
- **Don't restate the docs.** Before adding a line, check whether one docs page covers it. If it does, link that page with an explicit fetch instruction and add nothing else. Only judgment the docs lack (decisions, rules agents get wrong, traps scattered across pages) goes in, one line each with a link.
- **Docs are wrong? Fix the docs.** Open a PR in `hypertrack/hypertrack-content` instead of patching around it in the skill. A temporary one-liner is fine until the fix ships, with a TODO to remove it.
- **Size budget:** `SKILL.md` ≤ 200 lines and all skill Markdown ≤ 300 lines, enforced by `just budget` (part of `just check`). Raising the budget is a deliberate decision in its own commit, not a side effect.
- **Cut by content, not by file.** When trimming, ask of each line whether a docs page covers it and whether it's judgment. Don't delete or keep whole files wholesale.
- Placeholders are explicit (`YOUR_PUBLISHABLE_KEY`, `<version>`, `<order_handle>`). Credentials in examples come from environment variables.
- **Behavior gets a test.** Changes to `scripts/` or `tools/` need a regression test in `tests/`. Snippets with logic beyond API calls (such as webhook verification) get a behavior test there too; compiling isn't enough.
- `just check` before committing (dprint, script syntax, tests, links, API endpoints). `just snippets` when snippets or SDK versions change.
- When the skill's file structure changes, also update the Agent Skills docs page in `hypertrack/hypertrack-content` (`docs/content/guides/agent-skills.mdx`), which shows the tree.

## Distribution

- **skills CLI:** `npx skills add hypertrack/hypertrack-skills` (Claude Code, Codex, Cursor, Pi, and other Agent Skills agents)
- **Pi package:** `pi install git:github.com/hypertrack/hypertrack-skills` (uses the `pi.skills` manifest in `package.json`)
- **Manual:** copy or symlink `skills/hypertrack-integration/` into the agent's skills directory
