# HyperTrack Skills

Agent skill for end-to-end [HyperTrack](https://hypertrack.com) integration. Covers mobile SDK setup, backend API integration, webhooks, and verification across all supported platforms.

## What it covers

- **Mobile SDK** — iOS, Android, React Native, Expo, Flutter, Ionic Capacitor, .NET MAUI
- **Backend APIs** — Orders (shift tracking), Workers, Places, Nearby search
- **Webhooks** — Real-time order events, risk detection, geofence events
- **Verification** — End-to-end checklist and troubleshooting

## Installation

### Pi

```bash
pi install git:github.com/hypertrack/hypertrack-skills
```

### Claude Code

Clone and add to your skills directory:

```bash
git clone https://github.com/hypertrack/hypertrack-skills.git ~/.claude/skills/hypertrack-skills
```

Or use [skills.sh](https://skills.sh):

```bash
npx skills add hypertrack/hypertrack-skills
```

### Manual (any agent)

Point your agent at the skill entry point:

```
skills/hypertrack-integration/SKILL.md
```

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

- *"Integrate HyperTrack into my iOS app"*
- *"Set up shift tracking with pre-shift risk detection"*
- *"Add HyperTrack order tracking to my Node.js backend"*
- *"Debug why my HyperTrack worker isn't showing on the dashboard"*
- *"Set up webhooks to detect late arrivals"*

The skill routes to the appropriate reference based on your request.

## HyperTrack resources

- [Documentation](https://hypertrack.com/docs)
- [API Reference](https://hypertrack.com/reference)
- [Dashboard](https://dashboard.hypertrack.com)
- [FAQ](https://hypertrack.com/faq)

## License

MIT
