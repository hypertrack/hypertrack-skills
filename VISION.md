# Vision

**Make HyperTrack integration a one-prompt operation.**

A customer with a coding agent should be able to say "integrate HyperTrack into my app" and get a correct, production-ready integration — mobile SDK, backend API, webhooks, and verification — without reading docs or attending onboarding calls.

## Principles

- **Orders-first:** The skill teaches the recommended integration path (Orders API). Alternative approaches exist but are not the default.
- **Correct by default:** Code examples, field names, coordinate ordering, and API calls should be copy-pasteable and correct. An agent following this skill should not produce misintegrated apps.
- **Validate, don't trust:** Each phase includes verification steps. The skill should guide agents to confirm each step works before proceeding.
- **Platform-aware:** The skill supports all HyperTrack SDK platforms. Platform-specific details live in references, not in the main skill body.

## Success criteria

1. An agent using this skill can take a customer from zero to a working HyperTrack integration in one session
2. The integration passes HyperTrack's own integration review criteria
3. Common pitfalls (wrong coordinates, missing push, permission issues) are caught before they become production bugs
4. The skill stays current with HyperTrack's API and SDK releases
