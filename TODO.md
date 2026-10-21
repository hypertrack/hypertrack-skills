# TODO

## Now

1. [x] Land hypertrack/hypertrack-content#505 (docs fixes the skill will link to: SDK snippets, on-device orders, MAUI on .NET 10, webhook `.md` pages)
2. [x] Slim the skill to routing + judgment (VISION.md): `SKILL.md` plus a short `testing.md`, under `just budget`, which is part of `just check`
3. [ ] Before merging PR #1: run one real agent session with the slim skill and one with `main`'s skill on the same task (e.g. the iOS quickstart with HyperTrack removed). Does it fetch the linked pages, build, and pass the device checklist? If it doesn't follow the pointers, rethink before going further. Then squash-merge.
4. [ ] Update the Agent Skills docs page (`hypertrack-content/docs/content/guides/agent-skills.mdx`) to show the slim file tree
5. [ ] Publish the `sdk-maui` 1.0.4 GitHub release and changelog (it's on NuGet since January)

## Next

- [ ] Compile the SDK code snippets in the docs: hypertrack/hypertrack-content#509
- [ ] Review with the HyperTrack team for accuracy
- [ ] When the React Native Android orders-replay fix ships, state the minimum `hypertrack-sdk-react-native` version in the skill
- [ ] Broaden the agent runs: the other quickstarts with HyperTrack removed (Android, RN, Expo, Flutter) plus a Node and a Python backend
- [ ] CI: run `just check` on PRs

## Later

- [ ] Explore Claude Code plugin format (`.claude-plugin/plugin.json`) for marketplace distribution
