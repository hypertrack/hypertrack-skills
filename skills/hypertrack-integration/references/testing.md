# Testing and troubleshooting

## What an agent can verify alone

Credentials go in the environment (`HYPERTRACK_ACCOUNT_ID`, `HYPERTRACK_SECRET_KEY`). Run the commands from the skill directory, or use the full script path.

```bash
python3 scripts/ht.py check                       # credentials valid
python3 scripts/ht.py worker <worker_handle>      # linked device, status, last location, permissions
python3 scripts/ht.py track <worker_handle> --lat 37.795409 --lon -122.393403 --radius 150 --mode on_shift
python3 scripts/ht.py order <order_handle>        # status, timestamps, risks, share/embed URLs
python3 scripts/ht.py webhooks <order_handle>     # what HyperTrack sent and how your endpoint answered
python3 scripts/ht.py complete <order_handle>     # or: cancel <order_handle>
python3 scripts/ht.py sign body.json              # expected x-hypertrack-signature for a raw body
```

- `track` creates a **real** order that makes the worker's device track. Use a test worker, and complete or cancel the order afterwards.
- With the backend running, exercise its own code path (its job or endpoint that calls `/orders/track`), then use `order` and `webhooks` to confirm the result.
- Webhook handler: replay a captured body with the signature from `ht.py sign`, then with a wrong one. Expect 2xx and then 401.
- Mobile: `python3 scripts/audit_mobile.py <repo-root>` should report no `FAIL` lines, and the app must build for each platform.

## Device test protocol (needs a person and a phone)

Run this on a **physical device** with a debug or internal build. Give the user the steps and ask for the results.

1. Fresh install, log in. `ht.py worker <handle>` shows a device linked to the worker.
2. Grant permissions through the app's flow. On iOS choose Always and keep Precise on; on Android choose "Allow all the time". The app's SDK error list is empty.
3. Send the app to the background by switching apps. Don't swipe it away on iOS or force-stop it on Android (see the traps below).
4. `ht.py track <handle> … --mode on_shift` at a location near the device. Within a few minutes, `ht.py order <handle>` shows `started_at`, and the order's `embed_url` shows the device moving.
5. Walk into and out of the geofence, or use a test location. `arrived_at` / `exited_at` are set, and the `arrived` / `exited` webhooks reached your endpoint (`ht.py webhooks`).
6. If the app has clock-in: it's enabled only inside the geofence, and a `geotag` webhook arrives.
7. `ht.py complete <order>`. The device stops tracking (the location indicator disappears on iOS; the foreground notification disappears on Android).
8. Log out, then track a new test order for the same worker. This device must not start tracking. Cancel the order.

## Traps that look like bugs

| Trap                                                                                           | What happens                                                                                                                                                         |
| ---------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Android **force stop** (Settings → Force stop, Android Studio stop, `adb shell am force-stop`) | FCM delivery to the app is blocked until the user opens it manually, so remote start fails. Reboot or swipe away instead.                                            |
| iOS app **swiped away (force-quit)**                                                           | Silent pushes don't wake it. Tracking resumes when the worker opens the app.                                                                                         |
| iOS silent push **throttling**                                                                 | iOS delivers only a few silent pushes per hour per app. Rapid create/complete cycles while testing get dropped. Space tests out or open the app.                     |
| **Mock locations** (GPX on device, fake-GPS apps)                                              | Filtered by default and recorded as an outage. Set `HyperTrackAllowMockLocation` in QA builds only. The Android emulator and iOS simulator locations aren't flagged. |
| **Simulator / emulator**                                                                       | Fine for the UI and SDK calls. Use a physical device to test push wake-up and background tracking.                                                                   |
| **Permissions only When In Use**                                                               | Tracking can't start in the background (`insufficientForBackground`). It starts when the app comes to the foreground.                                                |
| **Debug build vs Firebase config**                                                             | Application ID or signing doesn't match `google-services.json` / the FCM key's project, so no push.                                                                  |
| **Name/metadata set via API**                                                                  | SDK `name` / `metadata` changes appear ignored. API values take precedence.                                                                                          |

Check FCM delivery on Android with the Firebase debug menu: dial `*#*#426#*#*` → Events.

## Symptoms

| Symptom                                         | Check, in order                                                                                                                                                                                                                                                          |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 401 from the API                                | AccountID:SecretKey pair (not the publishable key), base64 of `"id:secret"` as one string, stray whitespace or newline in env vars                                                                                                                                       |
| 400 on `/orders/track`                          | `detail` in the response body. Common causes: missing `track_mode` or `order_handle` / `destination`, malformed GeoJSON, an unclosed polygon                                                                                                                             |
| 409 on `/orders/track`                          | Handle already used (`duplicate_resource`). Check `GET /orders/{handle}` before retrying.                                                                                                                                                                                |
| Worker never appears                            | App never set the worker handle (or set `""`), wrong or missing publishable key (SDK error `invalidPublishableKey`), app not launched since install                                                                                                                      |
| Order created, device doesn't start             | Push setup (dashboard keys uploaded, iOS capability and Background Modes, Android Firebase config matches the key's project), permissions (`ht.py worker` → `location_permission`), traps above. Opening the app should start tracking; if it does, push is the problem. |
| Tracking stops when backgrounded                | iOS: Always permission and Background Modes. Android: background permission, OEM battery saver (whitelisting), outages `tracking_service_terminated` / `sdk_killed_by_user`                                                                                              |
| No arrival detected                             | Swapped coordinates, radius too small for the site (try 100–200 m), indoor GPS drift, wrong destination. Compare `GET /orders/{h}` destination with the real site.                                                                                                       |
| Device keeps tracking after work                | Some order is still `ongoing` for the worker (`GET /orders/?worker_handle=…&status=ongoing`), or the app set `isTracking = true` locally                                                                                                                                 |
| Webhooks missing / duplicated / signature fails | `webhooks.md` § Debugging delivery                                                                                                                                                                                                                                       |
| Clock-in button never enables                   | Order not on the device yet (it must be tracked for this worker and synced), location error in `isInsideGeofence`, geofence too small                                                                                                                                    |
| Device missing from Nearby results              | Availability set server-side only (doesn't reach the device), no recent location, outside `search_radius`, profile filter mismatch                                                                                                                                       |

## Outages

When tracking is interrupted, HyperTrack records an outage with a machine-readable `outage_code` and an `outage_category`. You see these in the dashboard and order timelines, in `GET /workers/{h}` / `GET /orders/{h}`, and as `outage_started` / `outage_ended` webhooks.

| Category       | Responsible party | Examples                                                                                           |
| -------------- | ----------------- | -------------------------------------------------------------------------------------------------- |
| `behavioural`  | Worker            | Permission denied or downgraded, Location Services off, app force-stopped or swiped, airplane mode |
| `os`           | Operating system  | Killed for memory or resources, crash, suspended                                                   |
| `adversarial`  | Possible fraud    | Mocked location, device time changed (`time_offset_changed` webhook)                               |
| `sporadic`     | Environment       | No GPS fix                                                                                         |
| `reachability` | Server ↔ device   | Push failed, push token missing, provisional iOS authorization                                     |

Full code list: `https://hypertrack.com/reference/webhooks/outage-codes`. A longer description list: `https://hypertrack.com/docs/list-of-outages.md`.
