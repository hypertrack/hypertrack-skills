# Vision

**Make HyperTrack integration a one-prompt operation.**

A customer with a coding agent should be able to say "integrate HyperTrack into my app" and get a correct, production-ready integration covering the mobile SDK, backend API, webhooks, and verification, without reading docs or attending onboarding calls.

## Principles

- **The docs are the source; the skill routes to them.** For each task, the skill tells the agent which docs page, OpenAPI spec section, SDK reference, or quickstart to fetch, with an explicit instruction ("before writing iOS code, fetch `https://hypertrack.com/docs/install-sdk-ios.md`"). It doesn't restate what those pages say. A copy drifts out of sync and makes the agent trust two sources.
- **Only judgment the docs don't have.** The skill keeps decisions to settle with the user, rules agents get wrong, and traps scattered across several pages. One line each, with a link. If one docs page covers something, link to that page and don't add a line.
- **Fix the docs, not the skill.** When the docs are wrong or missing something, fix them in `hypertrack/hypertrack-content`. The skill doesn't carry patched copies. A temporary one-liner is fine until the docs fix ships, with a TODO to remove it.
- **Small on purpose.** A short `SKILL.md` that the agent reads fully beats a large one it skims. Every line must earn its place. When trimming, cut by content (is it in the docs? is it judgment?), not by file.
- **Orders-first.** The recommended path is backend-managed Orders. On-device orders are for offline-first apps; manual tracking intent only when asked.
- **Inspect, then act.** The agent reads the customer's repo first and works on whichever side it's in (mobile or backend). It records shared decisions so the other side matches.
- **Validate, don't trust.** The agent checks its own work where it can (the build, the API, webhook delivery) and gives a person a clear device checklist for the rest.

## Success criteria

1. An agent using this skill can take a customer from zero to a working HyperTrack integration in one session, and it fetches the docs pages the skill points to. This is measured with real agent runs, not assumed.
2. The integration passes HyperTrack's own integration review criteria.
3. Common pitfalls (missing push, permission timing, leaked secret key, unverified webhooks, swapped coordinates) are caught before they become production bugs.
4. The skill stays small and in sync: its links and API endpoints are checked by `just check`, and it holds no copies of docs content.
