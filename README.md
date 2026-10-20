# HyperTrack Skills

Agent skill for end-to-end [HyperTrack](https://hypertrack.com) integration. Your coding agent learns how HyperTrack works, which decisions to make, and how to verify the result. It covers the mobile SDK, the backend APIs, webhooks, testing, and go-live.

## What it covers

- **Mobile SDK:** iOS, Android, React Native, Expo, Flutter, Ionic Capacitor, .NET MAUI. Worker handle lifecycle, permissions, errors, clock-in/out with on-device geofencing, and on-device orders for offline-first apps.
- **Backend APIs:** the order lifecycle for shift and job tracking, Places, Workers, Nearby search, secure embeds, auth, and errors.
- **Webhooks:** delivery contract, signature verification, and the full event map, including worker outages.
- **Verification:** a static audit for mobile repos, a CLI for checking orders and webhook delivery on your account, a device test protocol, and troubleshooting.
- **Go-live:** secrets, App Store and Google Play review, Android battery whitelisting, monitoring.

## Installation

Install with [skills](https://skills.sh), which works with Claude Code, Codex, Cursor, Pi, GitHub Copilot, Gemini CLI, OpenCode, and [many other agents](https://github.com/vercel-labs/skills#supported-agents):

```bash
npx skills add hypertrack/hypertrack-skills
```

It detects the coding agents you have installed and adds the skill to the current project. Add `-g` to install it for all your projects instead. Update later with `npx skills update`.

To install by hand instead, copy or symlink `skills/hypertrack-integration/` into your agent's skills directory.

## Usage

Tell your agent what you need:

- _"Integrate HyperTrack into my iOS app"_
- _"Track shifts with pre-shift late-arrival alerts"_
- _"Add HyperTrack order tracking to my Node.js backend"_
- _"Only let workers clock in when they're at the site"_
- _"Debug why my HyperTrack worker isn't tracking"_

The agent inspects your repo first, settles the integration decisions with you, then implements and verifies.

For verification against your account, export `HYPERTRACK_ACCOUNT_ID` and `HYPERTRACK_SECRET_KEY` (Setup page in the dashboard) in the agent's environment. To let the agent query live account data as well, add the read-only [HyperTrack MCP server](https://hypertrack.com/docs/mcp-server).

## Skill structure

```
skills/hypertrack-integration/
├── SKILL.md                 # Model, rules, workflow, sources of truth
├── references/
│   ├── mobile.md            # Shared mobile rules
│   ├── ios.md               # iOS
│   ├── android.md           # Android
│   ├── cross-platform.md    # React Native, Expo, Flutter, Ionic Capacitor, .NET MAUI
│   ├── backend.md           # Orders, places, workers, nearby, embeds
│   ├── webhooks.md          # Webhook endpoint and event map
│   ├── testing.md           # Verification, device testing, troubleshooting
│   └── production.md        # Store review, whitelisting, go-live
└── scripts/
    ├── ht.py                # Account verification CLI
    └── audit_mobile.py      # Static mobile setup audit
```

## Development

```bash
just check      # dprint, script syntax, regression tests, links, API endpoints vs the live OpenAPI spec
just snippets   # compile Swift/Kotlin/TS/Dart/C# snippets against the latest SDK releases
```

## HyperTrack resources

- [Documentation](https://hypertrack.com/docs)
- [API Reference](https://hypertrack.com/reference)
- [Dashboard](https://dashboard.hypertrack.com)

## License

MIT
