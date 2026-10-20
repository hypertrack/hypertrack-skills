---
name: hypertrack-integration
description: Build, extend, or debug a HyperTrack integration. Covers the mobile SDK (iOS, Android, React Native, Expo, Flutter, Ionic Capacitor, .NET MAUI), the Orders, Workers, Places, and Nearby APIs, webhooks, verification, and go-live. Use when code touches HyperTrack (hypertrack SDK packages, v3.api.hypertrack.com, x-hypertrack-signature webhooks), or when adding shift, job, or visit workflows with HyperTrack, such as arrival ETAs, late-arrival alerts, on-site clock-in, timesheets, or nearby worker search.
---

# HyperTrack integration

HyperTrack helps shift and field work run without hassle. Workers get where they need to be, clock in when they arrive, and get paid for the time they worked. Ops teams see arrivals, delays, and time on site without chasing anyone. Your backend tells HyperTrack when work happens by creating **orders**. For the duration of that work, the mobile SDK provides location. HyperTrack turns it into ETAs, arrivals and exits, time on site, and timesheets, and reports them through webhooks, the API, and embeddable views.

## How it works

| Concept   | Your identifier                             | Notes                                                                       |
| --------- | ------------------------------------------- | --------------------------------------------------------------------------- |
| Worker    | `worker_handle` = your user ID              | Created when the app sets the worker handle. Can also be created via API.   |
| Device    | `device_id` (SDK-generated)                 | Linked to a worker by the worker handle. A worker can have several devices. |
| Order     | `order_handle` = your shift, job, or visit  | A unit of tracked work with a destination geofence and a `track_mode`.      |
| Place     | `place_handle` = your site or location ID   | A recurring destination. HyperTrack learns better boundaries over time.     |
| Ops group | `ops_group_handle` = your division / region | Optional grouping with a timezone.                                          |

**Tracking intent** decides when the device tracks. The SDK merges the server-side intent from orders with the device-side `isTracking`. A silent push delivers changes, and the app syncs again whenever it opens. Prefer these ways to control tracking, in this order:

1. **Backend Orders API**, the default: tracking starts when an order is tracked and stops when the worker's last active order is completed or cancelled.
2. **On-device orders** (native iOS 5.12.0+, Android 7.12.0+): only for offline-first apps that must start full order tracking with no connectivity.
3. **`isTracking` / `work_status`**: low-level switches. Use only when the user explicitly asks. A device-side `isTracking = true` persists after orders complete.

## Rules that must hold

1. **SecretKey stays on servers.** Mobile apps get only the publishable key. Never put AccountID or SecretKey in app code, mobile config, or client-side JS. Never commit them.
2. **Silent push on every platform.** Upload the APNs auth key (`.p8` plus Team ID) and the FCM service-account JSON on the dashboard [Setup page](https://dashboard.hypertrack.com/setup). Without them, remote start and stop depend on the worker opening the app.
3. **Worker handle lifecycle.** Set it on login and on every app launch while logged in. Set it to `""` on logout.
4. **Permissions before the shift.** Get background ("Always") and precise location in the foreground before work starts. The SDK cannot ask for permissions when a push starts tracking in the background.
5. **Coordinates.** GeoJSON (API, webhooks) is `[longitude, latitude]`. Every SDK location type is the opposite: latitude, then longitude. Pass them by name where the language allows it.
6. **Location only during work.** Start tracking with the work, and end every order with complete or cancel. Open orders keep the device tracking. HyperTrack's guidance is to use location only during working hours, which is also how you keep workers' trust and permissions.
7. **Webhooks.** The body is a JSON array. Verify `x-hypertrack-signature`, an HMAC-SHA1 hex digest of the raw body keyed with the SecretKey. Dedupe retries by `x-amz-sns-message-id`, and apply events in `recorded_at` order.
8. **Don't guess.** Check field names against the OpenAPI spec and SDK symbols against the SDK reference or quickstart (see [Sources of truth](#sources-of-truth)).

## Workflow

### 1. Inspect before editing

Find out which side this repo is: mobile, backend, or both. Customers usually keep them in separate repos, so do your side and write down the shared decisions (step 2) for the other.

- **Mobile:** run `python3 scripts/audit_mobile.py <repo-root>` (path relative to this skill's directory). It detects the platform and reports missing keys, capabilities, dependencies, push setup, and worker-handle calls.
- Find the login and logout code paths, and the screen where a worker starts work.
- Find the domain entity that should become an order (shift, job, visit, delivery) and its start time, end time, and location.
- Check what already exists: Firebase/FCM, APNs entitlement, a backend HTTP client, secret storage, webhook endpoints, background jobs or cron.
- If HyperTrack is already integrated, check its SDK version against the latest release and treat the rules above as an audit checklist.

### 2. Settle the decisions

Ask the user only for what the code can't tell you.

| Decision                  | Guidance                                                                                                                                                                                                 |
| ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| What is an order?         | One unit of work at one destination, usually a shift or a job. Use your stable ID as `order_handle`.                                                                                                     |
| `track_mode`              | `pre_shift`: ETA, delay, and no-show risk before arrival (set `scheduled_at`). `on_shift`: geofence entries and exits and time on site (set `expected_service_time`; no delay risk). `full_shift`: both. |
| When to start tracking    | `pre_shift`: customers typically start 90–120 min before `scheduled_at`. `on_shift`: about 30 min before. Start early enough for the push to land; iOS throttles silent pushes.                          |
| Destination               | Recurring site: create a Place and pass `place_handle`. One-off site: Point plus `radius` (meters), or a Polygon.                                                                                        |
| Who ends the order        | Your backend, when the shift or job ends: an explicit worker action, or a scheduled job for known end times.                                                                                             |
| Which events you need     | Lifecycle (`started`, `arrived`, `exited`, `completed`), risk (`delayed`, `risk_updated`), and worker outages (`outage_started`/`outage_ended`). Subscribe to what drives product behavior.              |
| Clock-in/out at the site? | Use geotags with the order handle, and enable the button when the SDK's on-device geofence check (`isInsideGeofence`) says the worker is there.                                                          |

Record the result as a short **HyperTrack contract** (handles, track mode, lead time, destination source, events) in the PR description or a docs file, so the mobile and backend sides match.

### 3. Implement

| Area                                                                                 | Read                                                               |
| ------------------------------------------------------------------------------------ | ------------------------------------------------------------------ |
| Mobile, any platform (shared rules, permissions, errors, clock-in, on-device orders) | `references/mobile.md`                                             |
| iOS / Android native setup and code                                                  | `references/ios.md`, `references/android.md`                       |
| React Native, Expo, Flutter, Ionic Capacitor, .NET MAUI                              | `references/cross-platform.md` (plus the native setup it links to) |
| Backend: orders, places, workers, nearby, embeds, auth, errors                       | `references/backend.md`                                            |
| Webhook endpoint                                                                     | `references/webhooks.md`                                           |

Get the latest SDK version from `https://api.github.com/repos/hypertrack/<repo>/releases/latest` (`tag_name`). The repos are `sdk-ios`, `sdk-android`, `sdk-react-native`, `sdk-expo`, `sdk-flutter`, and `sdk-ionic-capacitor`. Android plugin artifacts use the same version as `sdk-android`. For .NET MAUI, use NuGet (`https://api.nuget.org/v3-flatcontainer/hypertrack.sdk.maui/index.json`, last entry); its GitHub releases lag behind.

### 4. Verify

- **Backend and account** (needs `HYPERTRACK_ACCOUNT_ID` / `HYPERTRACK_SECRET_KEY` in the environment): `python3 scripts/ht.py check`, then `track`, `order`, `webhooks`, and `complete`. The `webhooks` command shows every webhook HyperTrack sent for an order, with your endpoint's HTTP status. Run `python3 scripts/ht.py --help`.
- **Mobile (static):** `python3 scripts/audit_mobile.py <repo-root>` should report no `FAIL` lines, and the app must build.
- **On a device** (needs a person with a phone): follow `references/testing.md`. It covers the test protocol and the traps that make tracking look broken when it isn't: force-stopped Android apps, force-quit iOS apps, and mock locations.

Don't report the integration as done until the device test passes, or until you've told the user exactly which device steps remain.

### 5. Go live

Read `references/production.md`: store review (background location, foreground service, privacy answers), Android battery whitelisting, outage follow-up, and a go-live checklist.

## Troubleshooting

Read `references/testing.md` § Symptoms. Common causes (HyperTrack's docs name push setup as the most common):

1. Push not configured (key not uploaded, missing capability, missing `google-services.json`).
2. Permissions not granted for background or precise location.
3. `worker_handle` not set, or set on a different device than expected.
4. Swapped coordinates.
5. Orders never completed.

## Sources of truth

Fetch these when a reference doesn't cover something. Don't fill gaps from memory.

| Need                                | Source                                                                                                                                             |
| ----------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| Exact API fields, enums, endpoints  | OpenAPI spec: `https://hypertrack.com/reference/openapi.yaml`                                                                                      |
| Any guide as Markdown               | Index: `https://hypertrack.com/docs/llms.txt`. Each guide: `https://hypertrack.com/docs/<slug>.md`.                                                |
| Webhook payload for one event type  | `https://hypertrack.com/reference/webhooks/<slug>` (overview: `https://hypertrack.com/reference/webhooks`)                                         |
| iOS SDK symbols                     | `https://hypertrack.github.io/mobile/sdk-ios/latest/documentation/hypertrack/hypertrack/`                                                          |
| Android SDK symbols                 | `https://hypertrack.github.io/mobile/sdk-android/latest/-hyper-track%20-s-d-k%20for%20-android/com.hypertrack.sdk.android/-hyper-track/index.html` |
| RN / Flutter / Ionic / MAUI symbols | `https://hypertrack.github.io/sdk-react-native/`, `/sdk-flutter/`, `/sdk-ionic-capacitor/`, `/sdk-maui/`                                           |
| Working example apps                | `https://github.com/hypertrack/quickstart-<platform>` (`ios`, `android`, `react-native`, `expo`, `flutter`, `ionic-capacitor`, `maui`)             |
| SDK changes between versions        | `CHANGELOG.md` in each `hypertrack/sdk-*` repo                                                                                                     |

Cordova (`cordova-plugin-hypertrack-v3`) isn't supported, even though a docs page still exists. For Ionic or other web-view apps, use Ionic Capacitor.

## Live account access (optional)

The read-only HyperTrack MCP server (`npx -y @hypertrack/mcp-server`, with `HYPERTRACK_ACCOUNT_ID` / `HYPERTRACK_SECRET_KEY`) lets an agent query live orders, workers, devices, and order webhooks. If it's connected, use it to inspect state. It can't create or change anything; `scripts/ht.py` covers that for testing. Setup: `https://hypertrack.com/docs/mcp-server.md`.
