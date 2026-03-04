# Backend API Integration

Base URL: `https://v3.api.hypertrack.com`
Auth: HTTP Basic — `Authorization: Basic {base64(AccountID:SecretKey)}`

All request/response bodies are JSON. Set `Content-Type: application/json` and `Accept: application/json`.

---

## Authentication

```bash
# Encode credentials
echo -n '{AccountID}:{SecretKey}' | base64

# Use in requests
curl -H 'Authorization: Basic {encoded}' https://v3.api.hypertrack.com/workers/
```

Most HTTP libraries support basic auth natively:

```python
import requests
response = requests.get(
    'https://v3.api.hypertrack.com/workers/',
    auth=(ACCOUNT_ID, SECRET_KEY)
)
```

```javascript
const response = await fetch('https://v3.api.hypertrack.com/workers/', {
    headers: {
        'Authorization': 'Basic ' + btoa(`${ACCOUNT_ID}:${SECRET_KEY}`)
    }
});
```

---

## Places API

Create and manage recurring destinations. Using places enables HyperTrack to learn better geofence boundaries over time.

### Create a place

```bash
curl -X POST https://v3.api.hypertrack.com/places/v1/ \
  -u '{AccountID}:{SecretKey}' \
  -H 'Content-Type: application/json' \
  -d '{
    "place_handle": "bellevue-hospital-nyc",
    "address": "462 First Avenue, Manhattan, New York, NY, United States",
    "metadata": {
        "workplace_id": "1GDR743",
        "type": "hospital"
    }
}'
```

If you have coordinates, provide a geometry for more precise geofencing:

```bash
curl -X POST https://v3.api.hypertrack.com/places/v1/ \
  -u '{AccountID}:{SecretKey}' \
  -H 'Content-Type: application/json' \
  -d '{
    "place_handle": "safeway-seattle-77656",
    "geometry": {
        "type": "Point",
        "coordinates": [-122.311965, 47.718096]
    },
    "radius": 200,
    "address": "Safeway, 12318 15th Ave NE, Seattle, WA 98125",
    "metadata": {
        "customer_id": 77656,
        "vendor_name": "Safeway"
    }
}'
```

> **Coordinate order:** GeoJSON uses `[longitude, latitude]`, not `[lat, lng]`. This is the most common integration mistake.

### Key create parameters

| Parameter      | Required                       | Description                                                                  |
| -------------- | ------------------------------ | ---------------------------------------------------------------------------- |
| `place_handle` | No (auto-generated if omitted) | Your unique identifier for this place                                        |
| `geometry`     | No                             | Point or Polygon. If omitted, address is geocoded to an approximate polygon. |
| `radius`       | No                             | Radius in meters (only when geometry is Point)                               |
| `address`      | No                             | Human-readable address. Used for geocoding if no geometry provided.          |
| `metadata`     | No                             | Arbitrary JSON for filtering and enrichment                                  |
| `name`         | No                             | Human-readable name                                                          |
| `place_type`   | No                             | Hint for geocoding: `shop`, `hospital`, `warehouse`, `office`, etc.          |
| `parkings`     | No                             | Parking locations near the place                                             |
| `checkins`     | No                             | Check-in/clock-in locations at the place                                     |

### List places

```bash
curl -s -u '{AccountID}:{SecretKey}' \
  'https://v3.api.hypertrack.com/places/v1/?limit=10'
```

Supports filtering by `place_handles`, `search_term`, `name`, location (`lat`/`lon`/`radius`), `geofence_type`, pagination.

### Update a place

```bash
curl -X PATCH https://v3.api.hypertrack.com/places/v1/{place_handle} \
  -u '{AccountID}:{SecretKey}' \
  -H 'Content-Type: application/json' \
  -d '{
    "address": "Updated address",
    "metadata": { "zone": "east" }
}'
```

### Places intelligence

Over time, HyperTrack infers better geofence boundaries from actual worker visit patterns. These appear as suggestions in the Places UI. You can apply suggestions via the API to improve entry/exit detection accuracy.

---

## Workers API

Workers are typically created automatically when `worker_handle` is set via the SDK. Use the API for pre-provisioning or enrichment.

### Create a worker

```bash
curl -X POST https://v3.api.hypertrack.com/workers/ \
  -u '{AccountID}:{SecretKey}' \
  -H 'Content-Type: application/json' \
  -d '{
    "worker_handle": "james@company.com",
    "name": "James Rodriguez",
    "profile": {
        "employee_id": "144223",
        "region": "northeast",
        "skills": ["ICU", "ER"]
    },
    "ops_group_handle": "east-coast"
}'
```

| Parameter          | Required | Description                                          |
| ------------------ | -------- | ---------------------------------------------------- |
| `worker_handle`    | Yes      | Your unique identifier (user ID, email, phone, etc.) |
| `name`             | No       | Display name                                         |
| `profile`          | No       | Arbitrary JSON (skills, region, manager, etc.)       |
| `ops_group_handle` | No       | Business division grouping                           |
| `schedule`         | No       | Work schedule for auto-start/stop                    |
| `home`             | No       | Worker home location                                 |

### List workers

```bash
curl -s -u '{AccountID}:{SecretKey}' \
  'https://v3.api.hypertrack.com/workers/?limit=10'
```

Supports filtering by `ops_group_handle`, `filter_status` (`active`/`inactive`/`disconnected`), `search_term`, `work_status`, pagination.

### Update a worker

```bash
curl -X PATCH https://v3.api.hypertrack.com/workers/{worker_handle} \
  -u '{AccountID}:{SecretKey}' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "James R.",
    "profile": { "skills": ["ICU", "ER", "Pediatrics"] }
}'
```

### Ops Groups (optional)

Group workers by business division:

```bash
curl -X POST https://v3.api.hypertrack.com/workers/ops-groups/ \
  -u '{AccountID}:{SecretKey}' \
  -H 'Content-Type: application/json' \
  -d '{
    "ops_group_handle": "east-coast",
    "ops_group_label": "East Coast Division",
    "timezone": "America/New_York"
}'
```

---

## Orders API

The core tracking API. Each order represents a tracked unit of work.

### Track orders (create + start tracking)

```bash
curl -X POST https://v3.api.hypertrack.com/orders/track \
  -u '{AccountID}:{SecretKey}' \
  -H 'Content-Type: application/json' \
  -d '{
    "worker_handle": "james@company.com",
    "track_mode": "pre_shift",
    "ops_group_handle": "east-coast",
    "orders": [
        {
            "order_handle": "shift-2025-03-04-001",
            "destination": {
                "place_handle": "bellevue-hospital-nyc"
            },
            "scheduled_at": "2025-03-04T14:00:00Z",
            "metadata": {
                "shift_type": "day",
                "department": "ICU"
            }
        }
    ]
}'
```

### Required fields

| Field                   | Required | Description                              |
| ----------------------- | -------- | ---------------------------------------- |
| `track_mode`            | Yes      | `pre_shift`, `on_shift`, or `full_shift` |
| `worker_handle`         | Yes*     | Worker to track (*or `device_id`)        |
| `orders[].order_handle` | Yes      | Your unique shift/job identifier         |
| `orders[].destination`  | Yes      | Where the work happens                   |

### Track mode selection

| Mode         | Use case                                 | What it does                                            |
| ------------ | ---------------------------------------- | ------------------------------------------------------- |
| `pre_shift`  | Monitor arrival risk before shift starts | Computes ETA, fires delay risks based on `scheduled_at` |
| `on_shift`   | Track time at destination during shift   | Monitors geofence entry/exit, time on site              |
| `full_shift` | Combined pre + on                        | Both ETA monitoring and geofence tracking               |

> `on_time` and `flex` are deprecated. Do not use them.

### Destination formats

**Option 1: Place handle (recommended for recurring destinations)**

```json
{ "destination": { "place_handle": "bellevue-hospital-nyc" } }
```

**Option 2: Point + radius**

```json
{
    "destination": {
        "geometry": { "type": "Point", "coordinates": [-73.976, 40.739] },
        "radius": 200,
        "address": "462 First Avenue, New York, NY"
    }
}
```

**Option 3: Polygon**

```json
{
    "destination": {
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [-73.977, 40.738],
                [-73.977, 40.740],
                [-73.975, 40.740],
                [-73.975, 40.738],
                [-73.977, 40.738]
            ]]
        }
    }
}
```

> Remember: GeoJSON coordinates are `[longitude, latitude]`.

### Optional order fields

| Field                   | Description                                                                      |
| ----------------------- | -------------------------------------------------------------------------------- |
| `scheduled_at`          | ISO 8601 time the worker should arrive. Enables delay risk detection.            |
| `expected_service_time` | Duration in seconds. Reference value for on-shift tracking.                      |
| `metadata`              | Arbitrary JSON for filtering/enrichment.                                         |
| `device_switch_mode`    | `manual`, `login`, or `closest_to_destination` — controls multi-device behavior. |

### Response

The track endpoint returns created orders with:

- `embed_url` — embeddable live tracking view
- `share_url` — shareable tracking link
- `route_handle` — route identifier

### Complete an order

```bash
curl -X POST https://v3.api.hypertrack.com/orders/shift-2025-03-04-001/complete \
  -u '{AccountID}:{SecretKey}' \
  -H 'Content-Type: application/json'
```

> When the last order for a worker is completed and there are no remaining orders, tracking stops automatically on the device (requires silent push notifications).

### Cancel an order

```bash
curl -X POST https://v3.api.hypertrack.com/orders/shift-2025-03-04-001/cancel \
  -u '{AccountID}:{SecretKey}' \
  -H 'Content-Type: application/json' \
  -d '{ "metadata": { "cancel_reason": "worker_reassigned" } }'
```

### Get order timeline

```bash
curl -s -u '{AccountID}:{SecretKey}' \
  'https://v3.api.hypertrack.com/orders/shift-2025-03-04-001'
```

Returns the full timeline: tracking started, location updates, geofence entries/exits, geotags, outages, completion.

### Update an order

```bash
curl -X PATCH https://v3.api.hypertrack.com/orders/shift-2025-03-04-001 \
  -u '{AccountID}:{SecretKey}' \
  -H 'Content-Type: application/json' \
  -d '{
    "metadata": {
        "ht_on_time_arrival": true,
        "ht_worked_shift": true
    }
}'
```

Use PATCH to add ground truth labels or update metadata after the fact.

### List orders

```bash
curl -s -u '{AccountID}:{SecretKey}' \
  'https://v3.api.hypertrack.com/orders/?status=completed&scheduled_at_date=2025-03-04&limit=50'
```

Supports extensive filtering: `status`, `worker_handle`, `place_handle`, `track_mode`, date ranges, `ops_group_handle`, pagination.

### Recurring shifts pattern

For workers at the same place on multiple days (e.g., Apr 1–15):

1. Set up a daily cron that creates the order each morning (e.g., `pre_shift` 2h before start)
2. Set up a daily cron that completes the order each evening
3. Each day gets its own `order_handle` (e.g., `shift-2025-04-01`, `shift-2025-04-02`)

---

## Nearby API

Find available workers near a work location for backfill or on-demand assignment.

**Prerequisites:** Workers must have `isAvailable = true` set via the SDK.

### Region search (by distance)

```bash
curl -X POST https://v3.api.hypertrack.com/nearby/v4 \
  -u '{AccountID}:{SecretKey}' \
  -H 'Content-Type: application/json' \
  -d '{
    "order": {
        "destination": {
            "geometry": { "type": "Point", "coordinates": [-73.976, 40.739] }
        }
    },
    "search_type": "region"
}'
```

### ETA search (by drive time)

```bash
curl -X POST https://v3.api.hypertrack.com/nearby/v4 \
  -u '{AccountID}:{SecretKey}' \
  -H 'Content-Type: application/json' \
  -d '{
    "order": {
        "destination": {
            "geometry": { "type": "Point", "coordinates": [-73.976, 40.739] }
        }
    },
    "search_type": "eta"
}'
```

Returns up to 1000 workers sorted by distance (region) or drive time (eta). Supports `search_filter` for radius limits, profile-based filtering, and specific worker lists.

---

## Embed Views

Each tracked order has an `embed_url` for a live tracking view (map + timeline).

### Direct embedding (development)

The `embed_url` returned from the track endpoint works directly in an iframe — no auth required. Suitable for development and testing.

### Secure embedding (production)

For production, exchange the embed URL for a scoped token:

```bash
curl -X POST https://v3.api.hypertrack.com/oauth/embed-token \
  -u '{AccountID}:{SecretKey}' \
  -H 'Content-Type: application/json' \
  -d '{
    "embed_url": "https://embed.hypertrack.com/trips/...",
    "grant_type": "client_credentials"
}'
```

The response `secure_embed_url` is time-limited and safe to expose to end users.

### Embedding use cases

| Application        | What to embed                                                 |
| ------------------ | ------------------------------------------------------------- |
| Worker app         | Shift summary after clock-out (timeline, hours, mileage)      |
| Live ops dashboard | Real-time worker location + risk indicators                   |
| Customer support   | Shift timeline attached to support tickets                    |
| Payroll/expense    | Per-shift distance, time, on-time metrics                     |
| Customer portal    | Live pre-shift arrival view (can obfuscate route for privacy) |
