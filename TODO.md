# TODO

## Now

- [x] Rewrite around model, rules, workflow, and sources of truth (SKILL.md + 8 references)
- [x] Compiled Swift/Kotlin/TS/Dart/C# snippets against the latest SDKs (`just snippets`)
- [x] Link and API-endpoint drift check against the live OpenAPI spec (`just refs`)
- [x] Verification CLI (`scripts/ht.py`) and static mobile audit (`scripts/audit_mobile.py`)
- [x] Docs fixes upstream: hypertrack/hypertrack-content#505 (SDK snippets, on-device orders, webhook Markdown versions)

## Next

- [ ] After #505 deploys, slim the skill to routing + judgment (VISION.md): explicit fetch instructions per task, one-line judgment with links, a short `testing.md`, and `check_refs.py`; drop restated docs content, the platform snippets, `check_snippets.py`, `ht.py`, and `audit_mobile.py`. Done when `just budget` passes.
- [ ] Run one real agent session on the same task with the current and the slim skill (e.g. the iOS quickstart with HyperTrack removed). Check whether it fetches the linked pages, builds, and passes the device checklist.

- [ ] Update the Agent Skills docs page (`hypertrack-content/docs/content/guides/agent-skills.mdx`) to show the new file tree
- [ ] After #505 deploys: point webhook links at `https://hypertrack.com/reference/webhooks/<slug>.md`
- [ ] When the React Native Android orders-replay fix ships, state the minimum `hypertrack-sdk-react-native` version in `cross-platform.md`
- [ ] Broaden the agent runs: the other quickstarts with HyperTrack removed (Android, RN, Expo, Flutter) plus a Node and a Python backend
- [ ] CI: run `just check` on PRs and weekly; run `just snippets` on a macOS runner when SDKs release
- [ ] Review with the HyperTrack team for accuracy and completeness
- [ ] Ask the SDK team to list `activity-service-google` in `sdk-android/PLUGINS.md`, and to publish the `sdk-maui` 1.0.4 GitHub release and changelog

## Later

- [ ] Explore Claude Code plugin format (`.claude-plugin/plugin.json`) for marketplace distribution
