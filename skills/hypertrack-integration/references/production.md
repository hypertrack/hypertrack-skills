# Going to production

## Secrets and keys

- SecretKey only in backend secret storage. Check the mobile repo for leaks (`audit_mobile.py` flags obvious ones). If the key was ever committed, treat it as compromised and ask HyperTrack to replace it.
- The publishable key is meant to ship in the app. Keep it in config, not scattered through code.
- Keep the APNs `.p8` and the FCM service-account JSON out of the repo. They live in the HyperTrack dashboard (and your vault).

## App Store (iOS)

- **Guideline 2.5.4 (background location):**
  - Make background location visibly necessary: a shift screen showing tracking is active, a map, an arrival status.
  - Write purpose strings that explain the benefit to the worker.
  - Ask for permission after the user action that starts tracking, not at launch. A dedicated explanation screen with a button works best.
  - Attach a review video (an unlisted link is fine) that shows the location-dependent features.
- **App Privacy answers:** Location → Precise Location; Identifiers → User ID and Device ID. All are for App Functionality, linked to the user, and not used for tracking across apps. HyperTrack's `device_id` is random, and it uses IDFV across reinstalls.
- While tracking is active iOS shows the location indicator (blue bar). That's expected and required for reliable tracking.

## Google Play (Android)

- **Background location declaration** (Play Console → App content → Location permissions): describe the user-facing feature that needs "all the time" location, plus a video.
- **Prominent disclosure** in the app before the background request. It must include "This app collects location data to … even when the app is closed or not in use". Request foreground location first, then background.
- **Foreground service permissions form** (targetSdk 34+): declare the location foreground-service use. Pick Geofencing if orders start tracking, or User-initiated tracking if workers start it. Include a video that shows the foreground notification.
- These forms appear only after uploading a qualifying build. EAS, Fastlane, and other automation can't fill them, so do one release manually.
- Customize the foreground notification (`HyperTrackForegroundNotificationTitle` / `Text`) so it clearly says that location is tracked.

## Android battery savers (whitelisting)

Samsung, Xiaomi/Redmi, Vivo, OnePlus, OPPO, and others kill background apps no matter what the SDK does. Only the worker can exempt the app.

- Ship in-app guidance per manufacturer. HyperTrack's video guides are at `https://hypertrack.com/docs/whitelisting.md`; see also `https://dontkillmyapp.com`.
- Symptoms: `tracking_service_terminated`, `sdk_killed_by_user` (the worker says they didn't kill the app, but used "clear all" or a memory cleaner), and repeated `location_services_disabled` on OnePlus.

## Operations

- Subscribe to `outage_started` / `outage_ended`. For behavioural codes, notify the worker with `outage_description`. Track outage rates per OS and manufacturer.
- Subscribe to `delayed` / `risk_updated` if you run pre-shift no-show or late-arrival workflows. Define which intensity triggers action.
- Watch your webhook endpoint's error rate. `GET /orders/{h}/webhooks` shows per-delivery status.
- Run a reconciliation job that completes or cancels HyperTrack orders whose shifts ended in your system.
- Optionally embed order views (`backend.md` § Live views) for ops and support.

## Go-live checklist

- [ ] SecretKey only server-side. Publishable key in app config.
- [ ] APNs key (production) and FCM key uploaded. A push-started order works on a release build on a physical device.
- [ ] Worker handle set on login and launch, cleared on logout. Handles match the backend's `worker_handle`.
- [ ] Permission flow: two-step, foreground, before the first shift. Error states shown to the worker with fixes.
- [ ] Orders created with the agreed `track_mode`, lead time, and destination. Coordinates are `[lon, lat]`.
- [ ] Every order is completed or cancelled. A reconciliation job exists.
- [ ] Webhook endpoint: signature verified on the raw body, fast 2xx, dedupe, `recorded_at` ordering, unknown events ignored.
- [ ] Device test protocol (`testing.md`) passed on iOS and Android, including background and killed-app cases.
- [ ] Store submissions prepared: App Store 2.5.4 and privacy answers; Play background location and foreground-service forms.
- [ ] Whitelisting guidance shipped for Android workers.
