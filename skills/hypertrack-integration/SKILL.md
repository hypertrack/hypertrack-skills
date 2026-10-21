---
name: hypertrack-integration
description: Build, extend, or debug a HyperTrack integration. Covers the mobile SDK (iOS, Android, React Native, Expo, Flutter, Ionic Capacitor, .NET MAUI), the Orders, Workers, Places, and Nearby APIs, webhooks, verification, and go-live. Use when code touches HyperTrack (hypertrack SDK packages, v3.api.hypertrack.com, x-hypertrack-signature webhooks), or when adding shift, job, or visit workflows with HyperTrack, such as arrival ETAs, late-arrival alerts, on-site clock-in, timesheets, or nearby worker search.
---

# HyperTrack integration

HyperTrack helps shift and field work run without hassle. Workers get where they need to be, clock in when they arrive, and get paid for the time they worked. Ops teams see arrivals, delays, and time on site without chasing anyone.

This skill doesn't repeat HyperTrack's docs. It tells you which page to fetch for each task, plus the judgment the docs don't spell out. Every docs guide is available as Markdown at `https://hypertrack.com/docs/<slug>.md` (index: `https://hypertrack.com/docs/llms.txt`). The API is defined in `https://hypertrack.com/reference/openapi.yaml`. **Fetch the page before writing the code it covers; don't work from memory.**

## How it works

- **Worker** = your user, identified by `worker_handle` (your user ID), which the app sets in the SDK.
- **Order** = one unit of work (a shift, job, or visit) at one destination, identified by `order_handle` (your ID). Your backend creates it with `POST /orders/track`. HyperTrack wakes the worker's device with a silent push and starts location for that work. Completing or cancelling the worker's last active order stops it.
- **Place** = a recurring destination, identified by `place_handle`. HyperTrack learns its real boundary from visits.
- **Results** come back as webhooks, through the API, and as embeddable views: ETAs, delays, arrivals and exits, time on site, timesheets, and outages with reasons.
- Prefer backend-managed orders. On-device orders (native iOS 5.12+, Android 7.12+) are only for offline-first apps that must start work with no connectivity. The SDK's `isTracking` and the `work_status` API are low-level switches; use them only when asked. Fetch `https://hypertrack.com/docs/track-work.md`.

## Rules agents get wrong

1. **SecretKey stays on the server.** The app gets only the publishable key. Never put AccountID or SecretKey in mobile code, client-side JS, or a committed file.
2. **Silent push on every platform.** The APNs key and the FCM service-account JSON must be uploaded on the dashboard [Setup page](https://dashboard.hypertrack.com/setup). Without them, start and stop wait until the worker opens the app. HyperTrack's docs name this as the most common reason tracking never starts.
3. **Worker handle:** set it on every login and app launch, and set it to `""` on logout. Fetch `https://hypertrack.com/docs/worker-setup.md`.
4. **Permissions before the shift.** Background ("Always" / "Allow all the time") and precise location must be granted in the foreground before work starts; a push can't trigger a permission prompt. On iOS ask When In Use first, then Always (asking for Always first leaves the app in "provisional" authorization). On Android, request background location as a separate second step after a prominent disclosure. Fetch `https://hypertrack.com/docs/ios-sdk-faq.md` and `https://hypertrack.com/docs/prepare-for-google-play-submission.md`.
5. **Coordinates:** the API and webhooks use GeoJSON `[longitude, latitude]`. Every SDK location type is latitude first. Pass them by name where the language allows.
6. **Location only during work.** Start it with the work, and end every order with complete or cancel. Open orders keep the device tracking. Fetch `https://hypertrack.com/docs/manage-tracking-permissions.md`.
7. **Verify webhook signatures on the raw body**, before any JSON parsing. Fetch `https://hypertrack.com/docs/stream-order-activity-markers-via-webhooks.md` (section "Validate webhook notifications").
8. **Don't guess** API fields or SDK symbols. Check the OpenAPI spec, the SDK reference, or a quickstart. The spec is 1.2 MB, so search it instead of reading it whole: `grep -n -A40 '^  /orders/track:'` for the path, then the same for the `$ref` schema names it points to (e.g. `'^    TrackOrdersRequest:'`).

## Workflow

### 1. Inspect the repo first

- Is this repo the mobile app, the backend, or both? Customers usually have separate repos. Do your side and write down the shared decisions (step 2) for the other side.
- Find: the platform and the existing HyperTrack version, if any; the login and logout code; the screen where a worker starts work; the entity that should become an order (shift, job, visit) with its time and location; existing Firebase/FCM and APNs setup; how the backend stores secrets; existing webhook endpoints and scheduled jobs.

### 2. Settle the decisions

Ask the user only what the code can't tell you, then record the answers (handles, track mode, lead time, destination source, events) in the PR description or a docs file so both sides match.

| Decision          | Guidance                                                                                                                                                                                                                 |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| What's an order?  | One unit of work at one destination. Use your own stable ID as `order_handle`, one order per occurrence (e.g. `shift-<id>-<date>`).                                                                                      |
| `track_mode`      | `pre_shift` for ETAs and late-arrival risk before the shift, `on_shift` for time on site, `full_shift` for both. Fetch `https://hypertrack.com/docs/shift-tracking.md`.                                                  |
| When to start     | For `pre_shift`, customers typically start 90–120 minutes before the shift (`https://hypertrack.com/docs/ncns-detection.md`); for `on_shift`, about 30 minutes before (`https://hypertrack.com/docs/shift-tracking.md`). |
| Destination       | Recurring site: a Place (`https://hypertrack.com/docs/places.md`). One-off: a point with a radius, or a polygon.                                                                                                         |
| Who ends it       | Your backend: on a worker action, or a scheduled job at the known end time.                                                                                                                                              |
| Which events      | Only what drives product behavior. Index: `https://hypertrack.com/reference/webhooks.md`. To help workers fix permission or app problems: `https://hypertrack.com/reference/webhooks/outage-codes.md`.                   |
| Clock-in at site? | Geotags on the order, with the button enabled by the SDK's on-device geofence check. Fetch `https://hypertrack.com/docs/geofenced-clock-in-out.md`.                                                                      |

### 3. Implement

Before writing the code for a task, fetch its page:

| Task                                                | Fetch                                                                                                                                                                                                                                                                                                                                                   |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| iOS app                                             | `https://hypertrack.com/docs/install-sdk-ios.md`                                                                                                                                                                                                                                                                                                        |
| Android app                                         | `https://hypertrack.com/docs/install-sdk-android.md`, `https://hypertrack.com/docs/fcm-service-account.md`, `https://hypertrack.com/docs/plugins.md`                                                                                                                                                                                                    |
| React Native / Expo                                 | `https://hypertrack.com/docs/install-sdk-react-native.md` / `https://hypertrack.com/docs/install-sdk-expo.md`                                                                                                                                                                                                                                           |
| Flutter / Ionic Capacitor / .NET MAUI               | `https://hypertrack.com/docs/install-sdk-flutter.md` / `https://hypertrack.com/docs/install-sdk-ionic-capacitor.md` / `https://hypertrack.com/docs/install-sdk-maui.md`                                                                                                                                                                                 |
| SDK config keys (mock locations, notification text) | `https://hypertrack.com/docs/sdk-config.md`                                                                                                                                                                                                                                                                                                             |
| Creating and ending orders                          | `https://hypertrack.com/docs/track-work.md`, `https://hypertrack.com/docs/shift-tracking.md`, then the `/orders` paths in the OpenAPI spec                                                                                                                                                                                                              |
| Workers, ops groups                                 | `https://hypertrack.com/docs/worker-setup.md`                                                                                                                                                                                                                                                                                                           |
| Workers with several devices                        | `https://hypertrack.com/docs/multi-device-workers.md`                                                                                                                                                                                                                                                                                                   |
| Nearby search, availability                         | `https://hypertrack.com/docs/assign-orders-to-nearby-drivers.md`, `https://hypertrack.com/docs/manage-worker-availability.md`                                                                                                                                                                                                                           |
| Webhook endpoint                                    | `https://hypertrack.com/docs/stream-order-activity-markers-via-webhooks.md`, `https://hypertrack.com/reference/webhooks.md`, then `https://hypertrack.com/reference/webhooks/<event>.md` per event                                                                                                                                                      |
| Embedded views                                      | `https://hypertrack.com/docs/embed-views-into-ops-dashboard.md`                                                                                                                                                                                                                                                                                         |
| SDK symbols                                         | iOS `https://hypertrack.github.io/mobile/sdk-ios/latest/documentation/hypertrack/hypertrack/`, Android `https://hypertrack.github.io/mobile/sdk-android/latest/-hyper-track%20-s-d-k%20for%20-android/com.hypertrack.sdk.android/-hyper-track/index.html`, others at `https://hypertrack.github.io/sdk-<react-native, flutter, ionic-capacitor, maui>/` |
| A working example                                   | `https://github.com/hypertrack/quickstart-<ios, android, react-native, expo, flutter, ionic-capacitor, maui>`                                                                                                                                                                                                                                           |

**Versions:** use the latest release, `tag_name` from `https://api.github.com/repos/hypertrack/sdk-<ios, android, react-native, expo, flutter, ionic-capacitor>/releases/latest`. Android plugin artifacts share the `sdk-android` version. For .NET MAUI, use NuGet (`https://api.nuget.org/v3-flatcontainer/hypertrack.sdk.maui/index.json`, last entry); its GitHub releases lag behind.

**Judgment the docs don't spell out:**

- Webhooks: don't let a late event reopen a finished order. Return 200 for event types you don't handle; new ones get added. Join on `order_handle` and `worker_handle`, not `device_id`. A worker can switch devices. A framework body parser (for example a global `express.json()`) breaks signature checks, so hash the raw bytes. The docs count any 200–4xx response as delivered, so return 5xx only when you want a retry.
- Backend: derive order handles from your own IDs so retries are safe. On `409 duplicate_resource`, `GET` the order before deciding what to do. Run a reconciliation job that completes or cancels HyperTrack orders whose work ended in your system. URL-encode handles in paths (`james%40co.com`).
- Availability set on the server (`work_status`) doesn't currently reach the device, so the SDK won't start collecting location for Nearby. When the device needs to react, set availability in the app.
- Expo: the HyperTrack config plugin adds native code, so it needs a native build (the prebuild step on the Expo install page); it won't run in Expo Go.
- Cordova (`cordova-plugin-hypertrack-v3`) isn't supported, even though a docs page exists. Use Ionic Capacitor.

### 4. Verify

Read `references/testing.md`. It covers what you can check yourself (the build, the API, webhook delivery), the device test a person has to run, and the traps that make a working integration look broken. Don't report the integration as done until the device test passes, or until you've told the user exactly which device steps remain.

The read-only HyperTrack MCP server (`https://hypertrack.com/docs/mcp-server.md`) is useful for inspecting live orders, workers, and order webhooks if the user has it connected.

### 5. Go live

Check before launch:

- [ ] SecretKey only on the server. The publishable key is in the app config.
- [ ] APNs (production) and FCM keys uploaded. A push-started order works on a release build on a physical device.
- [ ] Worker handle set on login and launch, cleared on logout, and equal to the backend's `worker_handle`.
- [ ] Permissions requested in two steps, in the foreground, before the first shift. SDK errors are shown to the worker with a way to fix them.
- [ ] Orders use the agreed track mode, lead time, and destination. Coordinates are `[longitude, latitude]`.
- [ ] Every order is completed or cancelled, and a reconciliation job exists.
- [ ] Webhook endpoint verifies signatures on the raw body, answers fast, and handles retries and ordering.
- [ ] Device test passed on iOS and Android (`references/testing.md`).
- [ ] App Store and Google Play submissions prepared: `https://hypertrack.com/docs/prepare-for-app-store-submission.md`, `https://hypertrack.com/docs/prepare-for-google-play-submission.md`.
- [ ] Android workers have battery-saver whitelisting guidance: `https://hypertrack.com/docs/whitelisting.md`.
