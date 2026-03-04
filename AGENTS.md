# AGENTS.md

Agent skill repository for HyperTrack integration.

## Repository structure

```
hypertrack-skills/
├── skills/
│   └── hypertrack-integration/
│       ├── SKILL.md                  # Main skill: phases, data model, routing, pitfalls
│       └── references/
│           ├── sdk-ios.md            # iOS SDK: SPM/CocoaPods, APNs, permissions, errors
│           ├── sdk-android.md        # Android SDK: Gradle, FCM, whitelisting, permissions
│           ├── sdk-cross-platform.md # React Native, Expo, Flutter, Ionic Capacitor, .NET MAUI
│           ├── backend-api.md        # REST API: Orders, Workers, Places, Nearby, Embed
│           ├── webhooks.md           # Webhook setup, order events, risk events, implementation
│           └── troubleshooting.md    # Diagnostics, common pitfalls, outage codes
├── README.md                         # Human-facing: install, usage, links
├── AGENTS.md                         # This file
├── VISION.md                         # Direction and goals
├── TODO.md                           # Next priorities
└── package.json                      # Pi package + npm metadata
```

## How the skill works

1. `SKILL.md` is the entry point — it covers the integration phases, data model, decision guidance, and critical pitfalls
2. SKILL.md routes to specific references when platform-specific or deep API detail is needed
3. References are self-contained — each covers one topic end-to-end with code examples and verification steps

## Key domain concepts

- **Orders API** is the primary tracking mechanism (not manual tracking)
- `track_mode`: `pre_shift`, `on_shift`, `full_shift` are the supported modes (`on_time`, `flex` are deprecated)
- GeoJSON coordinates are `[longitude, latitude]` — the most common integration mistake
- Silent push notifications (APNs + FCM) are mandatory for remote tracking
- `worker_handle` must be set on login and cleared on logout

## Editing guidelines

- Keep SKILL.md under ~300 lines — it's loaded into agent context on trigger
- References can be longer (200–500 lines) — they're loaded on demand
- Every code example should be copy-pasteable with placeholder values clearly marked
- API examples use curl for universality
- SDK examples show the primary language per platform (Swift for iOS, Kotlin for Android)
- Cross-platform reference shows the JS/Dart/C# API surface, delegates native setup to platform refs
- When HyperTrack docs or API change, update the relevant reference and SKILL.md if the change affects routing or pitfalls

## Distribution

- **Pi:** `pi install git:github.com/hypertrack/hypertrack-skills`
- **npm:** publish `hypertrack-skills` package (uses `package.json` with `pi.skills` manifest)
- **Claude Code / Cursor / others:** clone to agent skills directory
- **Manual:** point agent at `skills/hypertrack-integration/SKILL.md`
