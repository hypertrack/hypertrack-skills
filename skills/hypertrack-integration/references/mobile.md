# Mobile SDK: shared rules

These apply to every platform. Platform setup and code are in `ios.md`, `android.md`, and `cross-platform.md`.

## Setup checklist (every platform)

1. Add the SDK dependency at the latest version. On Android, add the plugin artifacts at the same version.
2. Set the publishable key in native config: `HyperTrackPublishableKey` in `Info.plist` and in `AndroidManifest.xml` `<meta-data>`, or the Expo plugin param.
3. iOS: enable Background Modes (Location updates, Remote notifications) and the Push Notifications capability, and add the location and motion purpose strings.
4. Silent push: upload the APNs `.p8` key plus Team ID, and the FCM service-account JSON, on the dashboard Setup page. The app must already receive push (APNs registration on iOS; Firebase with `google-services.json` on Android).
5. Set the worker handle on login and launch; clear it on logout.
6. Request location permissions in the foreground (see below).
7. Subscribe to SDK errors on the screen where work starts and show the worker how to fix each one.

Run `python3 scripts/audit_mobile.py <repo-root>` after setup. It checks items 1–5 statically.

## Worker handle lifecycle

- Set it right after a successful login, and on every launch where a session is restored. The SDK persists it, but setting it again is cheap and fixes drift.
- Use your stable internal user ID, the same value the backend uses as `worker_handle` in `POST /orders/track`. Don't use display names. Use an email only if it never changes.
- On logout, set it to `""`. Otherwise orders for the old user can keep tracking this device.
- The handle links a worker to this device. With several devices per worker, the backend's `device_switch_mode` decides which device tracks an order (see `backend.md`).

## Permissions

Tracking that starts from a push happens in the background. The app can't show permission prompts then, so get everything granted in the foreground before the first shift.

**iOS**

- Ask in two steps: `requestWhenInUseAuthorization()`, then `requestAlwaysAuthorization()` once When In Use is granted. Asking for Always first leaves the app in "provisional Always", which stops background locations (SDK error `permissions.location.provisional`, outage `location_unavailable_provisional_authorization`).
- Precise location must be on. If it's reduced, send the worker to Settings.
- If Always is denied, the app can't ask again. Deep-link to Settings with `UIApplication.openSettingsURLString`.

**Android**

- Ask in two steps: `ACCESS_FINE_LOCATION` (with `ACCESS_COARSE_LOCATION`) first. Once that's granted, request `ACCESS_BACKGROUND_LOCATION` as a separate request on Android 10+ (API 29+). On Android 11+ that request opens Settings, where the worker must pick "Allow all the time".
- Before each request, show a prominent disclosure screen. For background location, Google Play requires the text to include "This app collects location data to … even when the app is closed or not in use".
- Optional: `ACTIVITY_RECOGNITION` (Physical activity) if you add the `activity-service-google` plugin. It improves activity detection.
- Battery-optimization whitelisting is a separate, OEM-specific step (see `production.md`).

**Both:** the worker can revoke permissions at any time. Check the SDK errors on every foreground and before the worker starts work.

## Errors API

Each SDK exposes the current blocking errors (`errors` / `getErrors()`) and a subscription. Map them to worker-facing actions:

| Error (iOS / Android / JS names vary)                | Show the worker                                                       |
| ---------------------------------------------------- | --------------------------------------------------------------------- |
| permissions → location → denied                      | "Allow location access" and link to Settings                          |
| permissions → location → insufficientForBackground   | "Change location to Always / Allow all the time" and link to Settings |
| permissions → location → reducedAccuracy             | "Turn on Precise Location" and link to Settings                       |
| permissions → location → notDetermined (iOS)         | Run the permission flow                                               |
| permissions → location → provisional (iOS)           | "Change location to Always" and link to Settings                      |
| location → servicesDisabled                          | "Turn on Location Services"                                           |
| location → mocked                                    | Mock location app active and mocking not allowed                      |
| location → signalLost                                | Transient. Usually just show status.                                  |
| noExemptionFromBackgroundStartRestrictions (Android) | Open the app; the OS blocked starting tracking in the background      |
| invalidPublishableKey / blockedFromRunning           | Configuration problem. Log it and alert developers.                   |

Errors describe the device right now. Outages that already happened (app killed, push failed, and so on) show up in the dashboard timeline and in `outage_started` webhooks (`webhooks.md`), not in the errors API.

## Clock-in / clock-out (geotags)

To record when work actually started and ended at the site, add geotags tied to the order:

- `addGeotag(orderHandle, orderStatus, metadata)`, where the order status is clock-in, clock-out, or a custom string, and metadata is a JSON object.
- Optional variant with an `expectedLocation`: HyperTrack reports the `deviation` in meters between the actual and expected location.
- Geotags work offline. They're stored and sent when the device reconnects. They show up in the order timeline and as `geotag` webhooks.

**Gate the clock-in button on presence at the site.** `HyperTrack.orders` holds the worker's active orders. Each order exposes `isInsideGeofence`, a result of bool or location error, computed on the device against the order destination, so it works offline once the order has been received. Subscribe to orders to update the UI. If the order isn't there yet, keep clock-in disabled.

## Coordinates

Every SDK location type takes **latitude, then longitude**: Swift `Location(latitude:longitude:)`, Kotlin/Java and C# `Location(latitude, longitude)`, Dart `Location(latitude, longitude)`, JS `{ latitude, longitude }`. The API and webhooks use GeoJSON, which is the opposite (`[longitude, latitude]`). When converting between the two, do it in one helper. In Kotlin and C#, pass the values by name (`latitude = …`, `longitude = …`). Dart and Java can only pass them positionally.

## Availability (Nearby search)

`isAvailable = true` marks a worker as available for Nearby search, so HyperTrack collects their location for `POST /nearby/v4`. Set it from a worker-facing toggle ("available for work"). The backend can also set availability with `work_status`, but **server-side changes don't currently reach the device**. The SDK doesn't start collecting location, so the worker won't show up with a fresh position. When the device needs to react, set availability on the device.

## On-device orders (offline-first only)

The native iOS (5.12.0+) and Android (7.12.0+) SDKs can create and track orders on the device with `HyperTrack.orders.track(trackMode, orders)`, and end them with `HyperTrack.orders[handle].complete()` / `.cancel()`. Use this only when the app is offline-first and must start full order tracking without connectivity. Otherwise create orders from the backend.

Limits:

- Each order takes only a handle and a destination (a circle with center and radius in meters, or a polygon). `scheduled_at`, `metadata`, and the other Orders API fields aren't available.
- Not exposed by React Native, Flutter, Ionic, or MAUI.

Code is in `ios.md` and `android.md`.

## Name and metadata

`name` and `metadata` label the device in the dashboard and in webhooks. Values set with the backend API take precedence over values set by the SDK. If SDK changes don't show up, check whether the backend set them.

## SDK configuration keys

Set these in `Info.plist` or as `AndroidManifest.xml` `<meta-data>`. In `Info.plist`, booleans must be of Boolean type (`<true/>`/`<false/>` in XML, YES/NO in Xcode's editor), not strings.

| Key                                     | Platform | Purpose                                                                                                        |
| --------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------- |
| `HyperTrackPublishableKey`              | Both     | Required.                                                                                                      |
| `HyperTrackAllowMockLocation`           | Both     | Default false: mocked locations are dropped and an outage is recorded. Enable only in QA builds.               |
| `HyperTrackForegroundNotificationTitle` | Android  | String resource for the foreground-service notification title.                                                 |
| `HyperTrackForegroundNotificationText`  | Android  | String resource for the notification text. It should say that location is being tracked.                       |
| `HyperTrackSwizzlingEnabled`            | iOS      | Set to false only if swizzling conflicts (e.g. Flutter + Firebase). Then forward AppDelegate calls (`ios.md`). |
