# Testing

## What you can check yourself

Build every platform you touched. For the API, use credentials from the environment (`HYPERTRACK_ACCOUNT_ID`, `HYPERTRACK_SECRET_KEY`, from the dashboard Setup page), never from the app:

```bash
AUTH="$HYPERTRACK_ACCOUNT_ID:$HYPERTRACK_SECRET_KEY"
API=https://v3.api.hypertrack.com

# Track a test order for a TEST worker. It starts location on that worker's device. GeoJSON is [longitude, latitude].
curl -sS -u "$AUTH" -H 'Content-Type: application/json' -X POST "$API/orders/track" -d '{
  "worker_handle": "<test-worker>", "track_mode": "on_shift",
  "orders": [{"order_handle": "agent-test-1",
              "destination": {"geometry": {"type": "Point", "coordinates": [<longitude>, <latitude>]}, "radius": 150}}]}'

curl -sS -u "$AUTH" "$API/orders/agent-test-1"            # status, started_at, arrived_at, timeline
curl -sS -u "$AUTH" "$API/orders/agent-test-1/webhooks"   # what HyperTrack sent, with your endpoint's delivery_http_status
curl -sS -u "$AUTH" -X POST "$API/orders/agent-test-1/complete"   # always end test orders
```

Better still, run the backend's own code path that tracks orders, then inspect the result with the calls above. With the HyperTrack MCP server connected, its `get_order` and `get_order_webhooks` tools do the same reads.

Webhook signature: replay a captured raw body to your endpoint with the right signature (expect 2xx) and a wrong one (expect it rejected). The expected signature:

```bash
python3 -c 'import hashlib, hmac, os, sys; print(hmac.new(os.environ["HYPERTRACK_SECRET_KEY"].encode(), sys.stdin.buffer.read(), hashlib.sha1).hexdigest())' < body.json
```

## Device test (needs a person with a phone)

Use a physical device and a debug or internal build. Give the user these steps and ask for the results:

1. Fresh install, then log in. The worker appears on the dashboard.
2. Grant permissions through the app's own flow: iOS Always with Precise on, Android "Allow all the time". The app shows no SDK errors.
3. Switch to another app. Don't swipe the app away on iOS or force-stop it on Android (see the traps below).
4. Track a test order near the device. The order shows `started_at`, and its `embed_url` shows the device. If it only starts once the app is opened, push isn't working.
5. Walk into and out of the destination. `arrived_at` and `exited_at` are set, and the webhooks reached your endpoint.
6. If the app has clock-in: the button is enabled only on site, and a `geotag` webhook arrives.
7. Complete the order. Location stops (the iOS location indicator and the Android notification go away).
8. Log out, then track another test order for the same worker. This device must not start. Cancel the order.

## Traps that look like bugs

- **Android force stop** (Settings, Android Studio, or `adb shell am force-stop`) blocks push until the user opens the app: `https://hypertrack.com/docs/android-sdk-faq.md`.
- **iOS apps swiped away** don't get silent pushes, and iOS throttles silent pushes during rapid testing: `https://hypertrack.com/docs/hypertrack-tracking-start-flow-technical-deep-dive.md`.
- **Mock locations** are dropped and recorded as an outage unless allowed in the build: `https://hypertrack.com/docs/mock-location.md`.
- **Simulators and emulators** are fine for UI and SDK calls. Use a physical device to test push and background behavior.
- **When In Use permission only:** tracking can't start in the background; it starts when the app comes to the foreground.
- **Debug builds** whose application ID or signature doesn't match the Firebase project don't get push: `https://hypertrack.com/docs/android-sdk-faq.md`.
- **Android battery savers** (Samsung, Xiaomi, OnePlus, and others) kill background apps: `https://hypertrack.com/docs/whitelisting.md`.

## Symptoms

| Symptom                                   | Check first                                                                                                          |
| ----------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| Worker never appears                      | The app never sets the worker handle, or the publishable key is wrong (SDK error `invalidPublishableKey`)            |
| Order created, device doesn't start       | Push keys and capabilities, permissions, the traps above. If opening the app starts it, push is the problem.         |
| Location stops in the background          | iOS Always permission and Background Modes; Android background permission and battery savers                         |
| No arrival detected                       | Swapped coordinates, or a radius too small for the site. Compare the order's destination with the real site.         |
| Device keeps going after work             | An order is still ongoing (`GET /orders/?worker_handle=<handle>&status=ongoing`), or the app set `isTracking` itself |
| Webhooks missing, duplicated, or rejected | `GET /orders/<order_handle>/webhooks` shows each delivery and your endpoint's response                               |
| Outage reasons on the dashboard           | `https://hypertrack.com/reference/webhooks/outage-codes.md`, `https://hypertrack.com/docs/list-of-outages.md`        |
