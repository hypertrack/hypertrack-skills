# Vision

**Make HyperTrack integration a one-prompt operation.**

A customer with a coding agent should be able to say "integrate HyperTrack into my app" and get a correct, production-ready integration covering the mobile SDK, backend API, webhooks, and verification, without reading docs or attending onboarding calls.

## Principles

- **Orders-first:** The skill teaches the recommended path, backend-managed Orders. Alternatives (on-device orders for offline-first apps, manual tracking intent) are documented with when to use them, not as defaults.
- **Judgment here, facts at the source:** The skill holds what docs don't give an agent: the model, decisions, invariants, traps, and verification. Volatile facts (fields, payloads, SDK symbols) point to the OpenAPI spec, docs `.md` versions, and SDK references instead of being copied.
- **Correct by construction:** Every snippet compiles against the latest SDK release and every endpoint exists in the OpenAPI spec. Both are checked by tooling, not by review.
- **Inspect, then act:** The agent reads the customer's repo first and works on whichever side it's in (mobile or backend). It records shared decisions so the other side matches.
- **Validate, don't trust:** Each phase ends with a check the agent can run itself (audit script, verification CLI), plus a clear device protocol for the parts only a human with a phone can test.
- **Platform-aware:** All HyperTrack SDK platforms are covered. Platform details live in references, not in the main skill body.

## Success criteria

1. An agent using this skill can take a customer from zero to a working HyperTrack integration in one session.
2. The integration passes HyperTrack's own integration review criteria.
3. Common pitfalls (wrong coordinates, missing push, permission timing, leaked secret key, unverified webhooks) are caught before they become production bugs.
4. The skill stays current with HyperTrack's API and SDK releases, and drift is detected by `just check` / `just snippets`.
