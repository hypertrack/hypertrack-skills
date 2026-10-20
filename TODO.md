# TODO

## Now

- [x] Rewrite around model, rules, workflow, and sources of truth (SKILL.md + 8 references)
- [x] Compiled Swift/Kotlin/TS/Dart/C# snippets against the latest SDKs (`just snippets`)
- [x] Link and API-endpoint drift check against the live OpenAPI spec (`just refs`)
- [x] Verification CLI (`scripts/ht.py`) and static mobile audit (`scripts/audit_mobile.py`)
- [x] Docs fixes upstream: hypertrack/hypertrack-content#505 (SDK snippets, on-device orders, webhook Markdown versions)

## Next

- [ ] Update the Agent Skills docs page (`hypertrack-content/docs/content/guides/agent-skills.mdx`) to show the new file tree
- [ ] After #505 deploys: point webhook links at `https://hypertrack.com/reference/webhooks/<slug>.md`
- [ ] When the React Native Android orders-replay fix ships, state the minimum `hypertrack-sdk-react-native` version in `cross-platform.md`
- [ ] Run real agent sessions as evals: quickstarts with HyperTrack removed (iOS, Android, RN, Expo, Flutter) plus a Node and a Python backend. Grade with `audit_mobile.py`, the build, and `ht.py`
- [ ] CI: run `just check` on PRs and weekly; run `just snippets` on a macOS runner when SDKs release
- [ ] Review with the HyperTrack team for accuracy and completeness
- [ ] Ask the SDK team to list `activity-service-google` in `sdk-android/PLUGINS.md`, and to publish the `sdk-maui` 1.0.4 GitHub release and changelog

## Later

- [ ] Explore Claude Code plugin format (`.claude-plugin/plugin.json`) for marketplace distribution
