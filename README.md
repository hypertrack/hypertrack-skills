# HyperTrack Skills

Agent skill for end-to-end [HyperTrack](https://hypertrack.com) integration. Covers mobile SDK setup, backend API integration, webhooks, and verification across all supported platforms.

## What it covers

- **Mobile SDK** — iOS, Android, React Native, Expo, Flutter, Ionic Capacitor, .NET MAUI
- **Backend APIs** — Orders (shift tracking), Workers, Places, Nearby search
- **Webhooks** — Real-time order events, risk detection, geofence events
- **Verification** — End-to-end checklist and troubleshooting

## Installation

Install with [skills](https://skills.sh), which works with Claude Code, Codex, Cursor, Pi, GitHub Copilot, Gemini CLI, OpenCode, and [many other agents](https://github.com/vercel-labs/skills#supported-agents):

```bash
npx skills add hypertrack/hypertrack-skills
```

It detects the coding agents you have installed and adds the skill to the current project. Add `-g` to install it for all your projects instead. Update later with `npx skills update`.

### Pi package

```bash
pi install git:github.com/hypertrack/hypertrack-skills
```

### Manual install

Copy or symlink `skills/hypertrack-integration/` into your agent's skills directory.

## Skill structure

```
skills/hypertrack-integration/
├── SKILL.md                      # Entry point: integration phases, data model, routing
└── references/
    ├── sdk-ios.md                # iOS SDK setup
    ├── sdk-android.md            # Android SDK setup
    ├── sdk-cross-platform.md     # RN, Expo, Flutter, Ionic, MAUI
    ├── backend-api.md            # Orders, Workers, Places, Nearby, Embed
    ├── webhooks.md               # Webhook setup, payloads, risk events
    └── troubleshooting.md        # Diagnostics, pitfalls, outage codes
```

## Usage

Tell your agent what you need:

- _"Integrate HyperTrack into my iOS app"_
- _"Set up shift tracking with pre-shift risk detection"_
- _"Add HyperTrack order tracking to my Node.js backend"_
- _"Debug why my HyperTrack worker isn't showing on the dashboard"_
- _"Set up webhooks to detect late arrivals"_

The skill routes to the appropriate reference based on your request.

## HyperTrack resources

- [Documentation](https://hypertrack.com/docs)
- [API Reference](https://hypertrack.com/reference)
- [Dashboard](https://dashboard.hypertrack.com)
- [FAQ](https://hypertrack.com/faq)

## License

MIT
