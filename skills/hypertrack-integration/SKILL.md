---
name: hypertrack-integration
description: End-to-end HyperTrack integration. Covers mobile SDK setup (iOS, Android, React Native, Flutter, Expo, Ionic Capacitor, .NET MAUI), backend APIs (Orders, Workers, Places), webhooks, and verification. Use when integrating HyperTrack location tracking, setting up shift/order tracking, debugging a HyperTrack integration, or working with HyperTrack APIs.
---

# HyperTrack Integration

Integrate HyperTrack location intelligence into your application. This skill covers the full lifecycle: mobile SDK → backend APIs → webhooks → verification.

## When to use

- Adding HyperTrack to a new or existing app
- Setting up shift tracking, order tracking, or workforce location monitoring
- Debugging an existing HyperTrack integration
- Working with HyperTrack Orders, Workers, or Places APIs

## Data model

HyperTrack tracks **workers** performing **orders** at **places**.

| Concept       | What it maps to                                  | Your identifier                         |
| ------------- | ------------------------------------------------ | --------------------------------------- |
| **Worker**    | Your app user (driver, courier, technician, rep) | `worker_handle` = your internal user ID |
| **Order**     | A unit of tracked work (shift, delivery, visit)  | `order_handle` = your shift/job ID      |
| **Place**     | A recurring destination (facility, store, site)  | `place_handle` = your location ID       |
| **Ops Group** | A business division or region (optional)         | `ops_group_handle` = your division ID   |

**Orders are the primary tracking mechanism.** Creating an order automatically starts tracking the assigned worker's device. Completing or cancelling it stops tracking. This is the recommended approach.

Alternatives (manual tracking via `work_status` API or local SDK `isTracking` toggle) exist but are not recommended for most integrations.

## Integration phases

Work through these in order. Each phase builds on the previous.

### Phase 1: Account setup

1. Sign up at https://dashboard.hypertrack.com/signup
2. From the [Setup page](https://dashboard.hypertrack.com/setup), collect:
   - **AccountID** + **SecretKey** → backend API auth (Basic auth, base64-encoded)
   - **Publishable Key** → mobile SDK configuration
3. Note the Webhooks section for later (Phase 5)
4. Verify API access:

```bash
curl -s -u '{AccountID}:{SecretKey}' https://v3.api.hypertrack.com/workers/ | head -c 200
```

A JSON response (even empty `{"data":[]}`) confirms credentials work.

### Phase 2: Mobile SDK integration

Platform-specific. Load the appropriate reference:

| Platform                                                | Reference                               |
| ------------------------------------------------------- | --------------------------------------- |
| iOS (Swift/ObjC)                                        | Read `references/sdk-ios.md`            |
| Android (Kotlin/Java)                                   | Read `references/sdk-android.md`        |
| React Native, Expo, Flutter, Ionic Capacitor, .NET MAUI | Read `references/sdk-cross-platform.md` |

**Get the latest SDK version** before installing. Each SDK publishes releases on GitHub:

| SDK             | Latest version                                                                             |
| --------------- | ------------------------------------------------------------------------------------------ |
| iOS             | `https://api.github.com/repos/hypertrack/sdk-ios/releases/latest` → `tag_name`             |
| Android         | `https://api.github.com/repos/hypertrack/sdk-android/releases/latest` → `tag_name`         |
| React Native    | `https://api.github.com/repos/hypertrack/sdk-react-native/releases/latest` → `tag_name`    |
| Flutter         | `https://api.github.com/repos/hypertrack/sdk-flutter/releases/latest` → `tag_name`         |
| Ionic Capacitor | `https://api.github.com/repos/hypertrack/sdk-ionic-capacitor/releases/latest` → `tag_name` |
| .NET MAUI       | `https://api.github.com/repos/hypertrack/sdk-maui/releases/latest` → `tag_name`            |

Fetch the `tag_name` from the GitHub API and use it wherever `<version>` appears in the install instructions.

**Every platform requires these steps — no exceptions:**

1. Add SDK dependency
2. Set publishable key in app config
3. **Set up silent push notifications** ← most common "tracking won't start" cause
4. Set `worker_handle` on login, clear to `""` on logout
5. Request location permissions (Always + Precise)
6. Subscribe to SDK errors

**Verification:** After SDK setup, run the app with permissions granted. The worker should appear on the [dashboard](https://dashboard.hypertrack.com).

### Phase 3: Places setup

For recurring work locations, create places once via API and reference them by `place_handle` in orders. This enables HyperTrack to learn better geofence boundaries over time.

**Skip this phase** if every order destination is unique — pass inline coordinates in the order instead.

→ Read `references/backend-api.md` § Places API

### Phase 4: Order tracking

The core integration. Your backend creates orders via the HyperTrack API when work is assigned.

**Key decisions:**

| Decision                    | Guidance                                                                                                                  |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| **Which `track_mode`?**     | `pre_shift` = risk monitoring before arrival. `on_shift` = geofence entry/exit during work. `full_shift` = both combined. |
| **When to start tracking?** | `pre_shift`: 90–120 min before `scheduled_at`. `on_shift`: ~30 min before. `full_shift`: whenever makes sense.            |
| **Destination format?**     | Use `place_handle` for recurring places. Use Point geometry + radius for one-off locations.                               |
| **When to stop tracking?**  | Call complete/cancel endpoint when shift ends. Use a cron for recurring shifts with known end times.                      |

→ Read `references/backend-api.md` § Orders API

### Phase 5: Webhooks

Receive real-time order events: started, arrived, delayed, risk alerts, completed, etc.

→ Read `references/webhooks.md`

### Phase 6: Verification & go-live

End-to-end checklist:

- [ ] API credentials work (Phase 1 curl test)
- [ ] Worker appears on dashboard when app runs
- [ ] Creating an order starts tracking on device
- [ ] Order timeline shows movement on dashboard
- [ ] Webhooks arrive at your endpoint
- [ ] Completing an order stops tracking
- [ ] No active tracking remains when all orders are done

**If something fails** → Read `references/troubleshooting.md`

## Geotags (optional enrichment)

Add clock-in/out or custom events to an order timeline from the mobile SDK:

| Platform             | Clock In                                                                    | Clock Out                                                                    |
| -------------------- | --------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| iOS/Android (native) | `HyperTrack.addGeotag(orderHandle, .clockIn, metadata)`                     | `HyperTrack.addGeotag(orderHandle, .clockOut, metadata)`                     |
| Cross-platform (JS)  | `HyperTrack.addGeotag(orderHandle, {type: "orderStatusClockIn"}, metadata)` | `HyperTrack.addGeotag(orderHandle, {type: "orderStatusClockOut"}, metadata)` |

Custom events: use `OrderStatus.Custom("event_name")` (native) or `{type: "orderStatusCustom", value: "event_name"}` (JS).

Geotags appear in the order timeline and webhook stream with location + deviation data.

## Embed views (optional)

Each tracked order returns an `embed_url` for a live tracking view. For production embedding, exchange it for a scoped token:

```bash
curl -X POST https://v3.api.hypertrack.com/oauth/embed-token \
  -u '{AccountID}:{SecretKey}' \
  -H 'Content-Type: application/json' \
  -d '{"embed_url": "<embed_url_from_order>", "grant_type": "client_credentials"}'
```

The response `secure_embed_url` can be safely embedded in iframes.

## Nearby search (optional)

Find available workers near a location for backfill/assignment:

1. Workers must have `isAvailable = true` set via SDK
2. Call `POST /nearby/v4` with destination coordinates and `search_type` (`region` or `eta`)

→ Read `references/backend-api.md` § Nearby API

## API quick reference

Base URL: `https://v3.api.hypertrack.com`
Auth: `Basic {base64(AccountID:SecretKey)}`

| Action             | Method | Endpoint                               |
| ------------------ | ------ | -------------------------------------- |
| Track orders       | POST   | `/orders/track`                        |
| Get order timeline | GET    | `/orders/{order_handle}`               |
| Update order       | PATCH  | `/orders/{order_handle}`               |
| Complete order     | POST   | `/orders/{order_handle}/complete`      |
| Cancel order       | POST   | `/orders/{order_handle}/cancel`        |
| List orders        | GET    | `/orders/`                             |
| Create worker      | POST   | `/workers/`                            |
| List workers       | GET    | `/workers/`                            |
| Update worker      | PATCH  | `/workers/{worker_handle}`             |
| Set work status    | POST   | `/workers/{worker_handle}/work_status` |
| Create place       | POST   | `/places/v1/`                          |
| List places        | GET    | `/places/v1/`                          |
| Update place       | PATCH  | `/places/v1/{place_handle}`            |
| Nearby search      | POST   | `/nearby/v4`                           |
| Secure embed token | POST   | `/oauth/embed-token`                   |

Full API reference: https://hypertrack.com/reference
OpenAPI spec (when available): https://developer.hypertrack.com/openapi/hypertrack-api.json

## Critical pitfalls

| Pitfall                                   | Impact                              | Fix                                                  |
| ----------------------------------------- | ----------------------------------- | ---------------------------------------------------- |
| Missing silent push notifications         | Tracking won't start/stop remotely  | Set up APNs (iOS) + FCM (Android). **Not optional.** |
| Wrong coordinate order                    | Orders created at wrong location    | GeoJSON = `[longitude, latitude]`, not `[lat, lng]`  |
| Not clearing `worker_handle` on logout    | Tracking continues under wrong user | Set to `""` on logout                                |
| Never completing orders                   | Tracking never stops, battery drain | Always call complete or cancel                       |
| Missing background location (Android 11+) | No tracking when app backgrounded   | Request `ACCESS_BACKGROUND_LOCATION`                 |
| Android battery optimization              | OS kills the app silently           | Whitelist app from battery saver                     |
| Webhook event ordering                    | Events processed out of sequence    | Sort by `recorded_at`, not arrival order             |
| Using deprecated track modes              | Unexpected behavior                 | Use only `pre_shift`, `on_shift`, `full_shift`       |

→ Full troubleshooting: Read `references/troubleshooting.md`
