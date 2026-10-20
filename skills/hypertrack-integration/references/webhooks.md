# Webhooks

HyperTrack POSTs events to one HTTPS endpoint per account. Payloads for every event type are at `https://hypertrack.com/reference/webhooks/<slug>`; the overview is `https://hypertrack.com/reference/webhooks`.

## Setup

1. Expose a static, public HTTPS endpoint. For local development, use a tunnel (ngrok, localtunnel, cloudflared).
2. Add the URL on the dashboard [Setup page](https://dashboard.hypertrack.com/setup) → Webhooks. Changes take up to 10 minutes to apply.
3. Leave **Include location updates** off unless you really need the raw location stream. It multiplies webhook volume 10–40×.
4. Use **Send test event** (⋯ menu on the webhook) to check reachability. The test payload is a `location`-type event from `TEST_DEVICE_ID`.

## Delivery contract

- `POST` with `Content-Type: application/json`. The body is **always a JSON array** of events, so iterate.
- The connection times out after **10 s**. Acknowledge fast and do the work asynchronously.
- Responses outside 200–4xx count as failed. HyperTrack retries **up to 3 times, 20 s apart**, with the same `x-amz-sns-message-id` header. **A 4xx counts as delivered and isn't retried.** Return 5xx (or time out) only when you want a retry.
- Delivery is usually in order but not guaranteed. **Order by `recorded_at`** (device time), not arrival time.

## Signature verification

`x-hypertrack-signature` = **HMAC-SHA1** of the **raw request body bytes**, keyed with the account **SecretKey**, as a lowercase hex digest. Compute it over the exact bytes received, before any JSON parsing or re-serialization, and compare in constant time.

Node (Express):

```js
const crypto = require('node:crypto');
const express = require('express');

const app = express();

function validSignature(rawBody, signature, secretKey) {
  const expected = crypto.createHmac('sha1', secretKey).update(rawBody).digest('hex');
  const a = Buffer.from(expected);
  const b = Buffer.from(String(signature || ''));
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}

// Raw body for this route only; a global express.json() would break the signature.
app.post('/webhooks/hypertrack', express.raw({ type: 'application/json' }), (req, res) => {
  if (!validSignature(req.body, req.get('x-hypertrack-signature'), process.env.HYPERTRACK_SECRET_KEY)) {
    return res.sendStatus(401);
  }
  const events = JSON.parse(req.body.toString('utf8'));
  enqueue(req.get('x-amz-sns-message-id'), events); // persist, then process async
  res.sendStatus(200);
});

function enqueue(messageId, events) {
  /* store and hand off to a worker */
}
```

Python (Flask; the same applies to FastAPI with `await request.body()`):

```python
import hashlib
import hmac
import json
import os

from flask import Flask, request

app = Flask(__name__)


def valid_signature(raw_body: bytes, signature: str | None, secret_key: str) -> bool:
    expected = hmac.new(secret_key.encode(), raw_body, hashlib.sha1).hexdigest()
    return hmac.compare_digest(expected, signature or "")


@app.post("/webhooks/hypertrack")
def hypertrack_webhook():
    raw = request.get_data()  # raw bytes, read before any JSON parsing
    if not valid_signature(raw, request.headers.get("x-hypertrack-signature"), os.environ["HYPERTRACK_SECRET_KEY"]):
        return "", 401
    events = json.loads(raw)
    enqueue(request.headers.get("x-amz-sns-message-id"), events)  # persist, then process async
    return "", 200


def enqueue(message_id, events):
    """Store and hand off to a worker."""
```

Use `python3 scripts/ht.py sign <body-file>` to compute the expected signature for a captured body.

## Processing rules

1. **Dedupe deliveries** by `x-amz-sns-message-id`; retries reuse it. Treat every event inside a delivery as distinct. Don't collapse events on a generic `(type, value, handle, recorded_at)` key: two geofence visits or two outage codes can share all of those. If you need idempotent writes, key them per event type and include the event's own identifiers, such as `data.marker_id` for geofences or `data.outage_code` for outages.
2. **Don't regress state.** A late `arrived` must not reopen a `completed` shift. Apply events in `recorded_at` order, and let terminal states win.
3. **Unknown types and values are normal.** New ones get added. Ignore them, and still return 200.
4. **Join on your handles:** `data.order_handle`, `worker_handle`, `data.place_handle`. Don't join on `device_id`; a worker can switch devices.
5. Coordinates in `location` / `data.*.location` are GeoJSON `[longitude, latitude]` (sometimes with altitude).

## Envelope

```json
[
  {
    "type": "order",
    "data": { "value": "arrived", "order_handle": "shift-5521-2026-11-03", "status": "ongoing" },
    "recorded_at": "2026-11-03T15:52:10.000Z",
    "created_at": "2026-11-03T15:52:12.000Z",
    "worker_handle": "user-8841",
    "device_id": "00112233-4455-6677-8899-AABBCCDDEEFF",
    "account_id": "…",
    "location": { "type": "Point", "coordinates": [-122.393403, 37.795409] },
    "version": "3.0.0"
  }
]
```

Dispatch on `type`, then on `data.value`.

## Event map

**`type: "order"`** (all carry `data.order_handle`, `data.status`, usually `route_handle`, `share_url`, `metadata`)

| `data.value`                                                                   | Meaning                                                                                                                                 | Typical action              |
| ------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------- | --------------------------- |
| `started`                                                                      | Tracking started for the order                                                                                                          | Mark the shift "tracking"   |
| `assigned` / `updated`                                                         | Order assigned to a worker or route; order fields changed                                                                               | Sync                        |
| `first_eta`, `eta`, `eta_change`                                               | ETA (`remaining_duration` s, `remaining_distance` m). `eta_change.change_reason`: `route_change` > `traffic_update` > `position_update` | Update ETA in your UI       |
| `n_minutes_away`                                                               | `remaining_minutes` from the destination                                                                                                | Notify the customer or site |
| `delayed`                                                                      | Predicted arrival (`arrive_at`) is after `scheduled_at`                                                                                 | Alert ops / backfill        |
| `risk_updated`                                                                 | `data.risks.<risk>.intensity_label` changed (`green`/`yellow`/`red`, plus `intensity_value` 0–1)                                        | Alert on red                |
| `arrived` / `exited`                                                           | Entered or left the destination geofence (`arrival` / `exit` with location and time; `place_handle`)                                    | Arrival / departure records |
| `on_device_geofence_checked`                                                   | Device-side inside-check result (`is_inside`, `outages` if unknown)                                                                     | Audit clock-in gating       |
| `device_switched`                                                              | Tracking moved to another device of the worker                                                                                          | Usually informational       |
| `disabled` / `enabled`                                                         | Order paused or resumed for later fulfillment                                                                                           | Sync                        |
| `completed` / `cancelled`                                                      | Order ended                                                                                                                             | Close the shift. Terminal.  |
| `billing_details_updated`, `timesheet_updated`, `location_timesheet_finalized` | Billable hours, breaks, and on-premises time computed from location                                                                     | Payroll / invoicing         |
| `planning_started` / `planning_completed` / `planning_failed`                  | Only with HyperTrack route planning (`POST /orders/`)                                                                                   | —                           |

Risk elements: `delayed_from_scheduled_at`, `delayed_from_initial_eta`, `is_offline`, `deviating_from_expected_route`, `moving_away_from_destination`, `in_low_battery`, `moving_too_slow`, `in_outage`.

**`type: "worker"`** (carry `worker_handle`, `device_id`)

| `data.value`                               | Meaning                                                                                                                                     |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `outage_started` / `outage_ended`          | Tracking blocked or restored. `outage_code` (machine-readable), `outage_category`, `outage_label`, `outage_description` (worker-facing fix) |
| `tracking_started`                         | First location received after tracking started                                                                                              |
| `work_status_updated`                      | `work_status.tracking` / `work_status.available` changed. `decision_source`: `business` or `hypertrack`                                     |
| `device_connected` / `device_disconnected` | Device regained or lost connectivity during tracking                                                                                        |
| `device_linked` / `device_unlinked`        | Worker linked to or unlinked from a device                                                                                                  |

**Permission revocation:** `outage_started` with `outage_category: "behavioural"` and an `outage_code` of `location_permissions_denied`, `location_permission_when_in_use_background`, `location_permission_imprecise`, `location_permission_not_determined`, `location_permission_restricted`, `location_services_disabled`, `foreground_service_denied` (Android), or `sdk_killed_permission_change` (Android). The matching `outage_ended` has the same code. Send the worker `outage_description` (for example by push or SMS) so they can fix it. Full list: `https://hypertrack.com/reference/webhooks/outage-codes`.

**Other types**

| `type`                                             | Payload                                                                                                                                                                                |
| -------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `geotag`                                           | `data.order_handle`, `order_status` (e.g. clock in/out label), `metadata`, `location`, optional `expected_location` + `deviation` (m), `distance`/`duration` since the previous geotag |
| `geofence`                                         | Place visit `data.value`: `entry` / `exit`, with `arrival`, `exit`, `duration`, `place_handle`, `geofence_metadata`                                                                    |
| `battery`                                          | `data.value`: `low` / `normal` / `charging`, with `battery_percent` (payload 2.1.0)                                                                                                    |
| `time_offset_changed`                              | Device clock changed by more than 10 min (`data.value` = offset in seconds, `user_time`). A fraud signal.                                                                              |
| `route`                                            | Route lifecycle (`created`, `assigned`, `started`, `updated`, `completed`, `candidate_devices_updated`, …)                                                                             |
| `registration`, `registration_update`, `reinstall` | Device registered, device info changed, or host app reinstalled                                                                                                                        |
| `location`, `device_status`, `trip`                | Legacy or deprecated streams. Don't build new logic on them.                                                                                                                           |

## Debugging delivery

- `python3 scripts/ht.py webhooks <order_handle>` (or `GET /orders/{order_handle}/webhooks`) lists every webhook HyperTrack sent for an order, with your endpoint's `delivery_http_status`, `retry_count`, and response text. Start here when "webhooks don't arrive".
- Not received at all: check the URL on the Setup page, that the endpoint is public HTTPS and answers a plain `curl -X POST` from outside, the 10 s timeout, and firewall or WAF rules.
- Duplicates: your endpoint returned 5xx or timed out, so it was retried. Dedupe by `x-amz-sns-message-id`.
- Signature mismatches almost always mean the body was parsed and re-serialized. Hash the raw bytes.
