# HyperTrack Skills

Agent skill for end-to-end [HyperTrack](https://hypertrack.com) integration. HyperTrack helps shift and field work run without hassle: on-time arrivals, clock-in at the site, and accurate hours and pay. With this skill, your coding agent learns how HyperTrack works, which decisions to make, and how to verify the result, across the mobile SDK, the backend APIs, webhooks, testing, and go-live.

## What it covers

- **Routing:** for each task (mobile SDK on any platform, orders, workers, places, Nearby search, webhooks, embedded views), the agent fetches the matching HyperTrack docs page as Markdown, the OpenAPI spec, or an SDK reference, instead of relying on memory.
- **Judgment the docs don't spell out:** the decisions to settle with you, the rules agents tend to get wrong, and webhook and backend habits.
- **Verification:** checks the agent can run itself, a device test for a person with a phone, and the traps that make a working integration look broken.
- **Go-live:** a checklist before launch.

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
- _"Alert us before a shift when a worker is running late"_
- _"Add HyperTrack order tracking to my Node.js backend"_
- _"Let workers clock in when they arrive at the site"_
- _"Debug why my HyperTrack worker isn't tracking"_

The agent inspects your repo first, settles the integration decisions with you, then implements and verifies.

To let the agent check its work against your account, export `HYPERTRACK_ACCOUNT_ID` and `HYPERTRACK_SECRET_KEY` (Setup page in the dashboard) in its environment, or connect the read-only [HyperTrack MCP server](https://hypertrack.com/docs/mcp-server).

## Skill structure

```
skills/hypertrack-integration/
├── SKILL.md            # Model, rules, workflow, which docs page to fetch for each task, go-live checklist
└── references/
    └── testing.md      # Verification, device test, traps, symptoms
```

## Development

```bash
just check   # size budget, formatting, links and API endpoints vs the live OpenAPI spec
```

## HyperTrack resources

- [Documentation](https://hypertrack.com/docs)
- [API Reference](https://hypertrack.com/reference)
- [Dashboard](https://dashboard.hypertrack.com)

## License

MIT
