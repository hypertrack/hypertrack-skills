# Webhooks

HyperTrack sends real-time events to your HTTPS endpoint as POST requests with JSON payloads.

## Setup

1. Create a publicly accessible HTTPS endpoint that accepts POST requests
2. Go to [HyperTrack Dashboard → Setup](https://dashboard.hypertrack.com/setup)
3. Enter your webhook URL in the Webhooks section

### Endpoint requirements

- **Static HTTPS URL** — must be accessible at all times
- **POST method** — all webhooks are POST requests
- **JSON parsing** — payloads are `application/json`
- **Respond within 10 seconds** — connection times out after 10s
- **Return 2xx or 4xx** — anything else triggers retries

> For local development, use [localtunnel](https://github.com/localtunnel/localtunnel) or ngrok to expose a local endpoint via HTTPS.

### Retries

If your endpoint doesn't return a success response, HyperTrack retries up to 3 times with 20-second delays. Each retry has the same `x-amz-sns-message-id` — use this to deduplicate.

### Signature verification

Each webhook includes an `x-hypertrack-signature` header. Verify this to ensure webhooks are genuinely from HyperTrack.

### Event ordering

HyperTrack attempts in-order delivery, but network issues can cause out-of-order arrival. **Always sort by `recorded_at`**, not by when webhooks are received.

---

## Payload structure

Every webhook POST body is a **JSON array** of event objects:

```json
[
    {
        "created_at": "2025-03-04T14:01:00.000000Z",
        "recorded_at": "2025-03-04T14:00:00.000000Z",
        "device_id": "00112233-4455-6677-8899-AABBCCDDEEFF",
        "worker_handle": "Worker-1",
        "account_id": "6784e919-7168-4f61-b686-2020f547637f",
        "type": "order",
        "data": { ... },
        "version": "3.0.0"
    }
]
```

> Always iterate over the array — multiple events can arrive in a single POST.

---

## Order lifecycle webhooks

These are the events you'll use most. All have `"type": "order"`.

### Order started

Fires when tracking begins for an order.

```json
"data": {
    "value": "started",
    "order_handle": "shift-001",
    "route_handle": "4359cc65-...",
    "status": "ongoing",
    "share_url": "https://trck.at/vr1RNLq",
    "metadata": { "shift_type": "day" }
}
```

### Order first ETA

First ETA estimate after tracking starts.

```json
"data": {
    "value": "first_eta",
    "order_handle": "shift-001",
    "remaining_distance": 2582,
    "remaining_duration": 410,
    "status": "ongoing",
    "share_url": "https://trck.at/vr1RNLq"
}
```

### Order ETA change

ETA updated due to position change, route recalculation, or traffic.

```json
"data": {
    "value": "eta_change",
    "order_handle": "shift-001",
    "remaining_distance": 2382,
    "remaining_duration": 359,
    "change_reason": "position_update",
    "status": "ongoing"
}
```

`change_reason` values: `position_update`, `route_change`, `traffic_update`

### Order delayed

Worker will arrive after `scheduled_at`.

```json
"data": {
    "value": "delayed",
    "order_handle": "shift-001",
    "status": "ongoing",
    "arrive_at": "2025-03-04T14:25:00.000Z",
    "scheduled_at": "2025-03-04T14:23:00.000Z",
    "initial_eta": "2025-03-04T14:20:00.000Z"
}
```

### Order N-minutes away

Worker is N minutes from destination.

```json
"data": {
    "value": "n_minutes_away",
    "order_handle": "shift-001",
    "remaining_distance": 2164,
    "remaining_duration": 300,
    "remaining_minutes": 5,
    "status": "ongoing"
}
```

### Order arrived

Worker entered the destination geofence.

```json
"data": {
    "value": "arrived",
    "order_handle": "shift-001",
    "status": "ongoing"
}
```

### Order exited

Worker left the destination geofence.

```json
"data": {
    "value": "exited",
    "order_handle": "shift-001",
    "status": "ongoing"
}
```

### Order completed

Order was completed via API.

```json
"data": {
    "value": "completed",
    "order_handle": "shift-001",
    "status": "completed"
}
```

### Order cancelled

Order was cancelled via API.

```json
"data": {
    "value": "cancelled",
    "order_handle": "shift-001",
    "status": "cancelled"
}
```

---

## Risk webhooks

Risk events fire when HyperTrack detects issues that may affect order fulfillment. These are critical for pre-shift monitoring.

### Orders at risk

```json
"data": {
    "value": "risk_updated",
    "order_handle": "shift-001",
    "status": "ongoing",
    "risks": {
        "delayed_from_scheduled_at": {
            "intensity_label": "red",
            "intensity_value": 0.85,
            "previous_intensity_label": "yellow"
        },
        "moving_away_from_destination": {
            "intensity_label": "yellow",
            "intensity_value": 0.45,
            "previous_intensity_label": "green"
        }
    }
}
```

### Risk elements

| Risk | Description |
|------|-------------|
| `delayed_from_scheduled_at` | Worker will be late based on `scheduled_at` |
| `delayed_from_initial_eta` | Worker will be later than the first ETA communicated |
| `is_offline` | Device not sending location updates |
| `deviating_from_expected_route` | Worker going off the expected route |
| `moving_away_from_destination` | Worker heading away from destination |
| `in_low_battery` | Device battery may die before order completion |
| `moving_too_slow` | Worker moving too slowly to arrive on time |
| `in_outage` | Location outage due to user action or software issue |

### Risk intensity

Each risk has an `intensity_label` (`green`, `yellow`, `red`) and `intensity_value` (0.0–1.0). Use these to set thresholds for alerting.

---

## Device and tracking webhooks

### Geofence entry/exit

Fires when a tracked device enters or exits any geofence.

```json
{
    "type": "geofence",
    "data": {
        "value": "entry",
        "arrival": {
            "location": { "type": "Point", "coordinates": [-122.394, 37.793] },
            "recorded_at": "2025-03-04T13:29:21.085Z"
        },
        "place_handle": "Store-North-Square",
        "marker_id": "00001111-b97b-...",
        "route_to": {
            "distance": 1234,
            "duration": 3600,
            "idle_time": 1800,
            "started_at": "2025-03-04T12:29:16.424Z"
        }
    }
}
```

On exit, `data.exit` is populated with exit location and time, and `data.duration` shows total visit duration in seconds.

### Geotag

Fires when a geotag is added from the SDK (clock-in/out, custom events).

```json
{
    "type": "geotag",
    "data": {
        "order_handle": "shift-001",
        "order_status": "arrived",
        "metadata": { "event": "clock_in" },
        "deviation": 14,
        "distance": 238,
        "location": { "type": "Point", "coordinates": [-6.2755, 57.64] },
        "expected_location": { "type": "Point", "coordinates": [-6.2756, 57.64] },
        "worker_handle": "James"
    }
}
```

`deviation` is the distance in meters between actual and expected location.

### Battery

Fires when device battery drops to "low" level.

```json
{
    "type": "battery",
    "data": {
        "value": "low",
        "battery_percent": 15
    }
}
```

### Time offset changed

Fires when a worker manually changes device time by >10 minutes (potential fraud signal).

```json
{
    "type": "time_offset_changed",
    "data": {
        "user_time": "2025-03-04T19:09:13.818Z",
        "value": 3584.235
    }
}
```

---

## Billing details webhook

Fires when billing details are updated for an order.

```json
"data": {
    "value": "billing_details_updated",
    "order_handle": "shift-001",
    "billing_details": {
        "billable_hours": 10,
        "travel_time": 10,
        "service_time": 10,
        "breaks": [
            {
                "id": "28315a00-...",
                "start_time": "2025-03-04T14:20:00.000Z",
                "end_time": "2025-03-04T14:30:00.000Z"
            }
        ]
    }
}
```

---

## Implementation guidance

### Recommended webhook handler pattern

```python
# Pseudocode
def handle_webhook(request):
    verify_signature(request.headers['x-hypertrack-signature'])
    events = request.json()  # Always an array

    for event in events:
        event_type = event['type']
        data = event['data']

        if event_type == 'order':
            order_handle = data['order_handle']
            value = data['value']

            if value == 'started':
                mark_shift_tracking_active(order_handle)
            elif value == 'risk_updated':
                process_risks(order_handle, data['risks'])
            elif value == 'arrived':
                mark_worker_arrived(order_handle)
            elif value == 'completed':
                mark_shift_complete(order_handle)
            elif value in ('delayed', 'n_minutes_away'):
                update_eta(order_handle, data)

    return 200
```

### Key implementation notes

1. **Idempotency:** Use `order_handle` + `data.value` + `recorded_at` as a dedup key
2. **Ordering:** Store and process by `recorded_at`, not arrival time
3. **Batch processing:** A single POST may contain multiple events — always iterate
4. **Risk thresholds:** Decide which `intensity_label` levels trigger action in your system
5. **Graceful handling:** Return 200 even for event types you don't handle yet
