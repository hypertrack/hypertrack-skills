# Backend API

Base URL `https://v3.api.hypertrack.com`. JSON in, JSON out. Field-level truth is the OpenAPI spec at `https://hypertrack.com/reference/openapi.yaml`. Check request and response shapes there before writing a client. Every endpoint and field named below exists in that spec.

## Auth and secrets

- **Basic auth:** `Authorization: Basic base64(AccountID:SecretKey)`. Most HTTP clients take `(user, password)`. This is the simplest option for server-to-server calls.
- **Bearer token (alternative):** `POST /oauth/token` with `{"grant_type": "client_credentials", "client_id": AccountID, "client_secret": SecretKey, "scope": "..."}`, then send `Authorization: Bearer <access_token>` until `expires_in` runs out. Scopes such as `read.embed.orders` restrict tokens you hand to embedded views. The default `*` is unrestricted.
- Read the credentials from the backend's secret store or environment, for example `HYPERTRACK_ACCOUNT_ID` / `HYPERTRACK_SECRET_KEY`. Never hard-code them, log them, or send them to a client.
- URL-encode handles in paths: a `worker_handle` of `james@co.com` becomes `/workers/james%40co.com`.

## Errors

Errors are RFC 7807-style JSON: `status`, `code`, `title`, `detail`, and sometimes `invalid_params`. The spec documents:

- `400`: validation (log `detail`, it names the field)
- `401`: wrong credentials (basic auth must be `base64("AccountID:SecretKey")`)
- `404`: unknown order or worker
- `409` `duplicate_resource` on `POST /orders/track`: an order or route with that handle already exists. Treat it as "already tracked" in idempotent retries; don't create a new handle blindly.

Retry only network errors and 5xx, with backoff. Never retry a 4xx unchanged.

## Orders: the integration core

### Lifecycle

```
POST /orders/track ─▶ ongoing ─▶ (arrived / exited, risks, ETAs …) ─▶ POST …/complete ─▶ completed
                          └────────────────────────────────────────▶ POST …/cancel   ─▶ cancelled
```

- Tracking a worker's first active order starts the device tracking (by silent push). Completing or cancelling the worker's **last** active order stops it.
- Use one order per occurrence of work. For a recurring shift, create a new order each day with its own `order_handle`, e.g. `shift-<shiftId>-<yyyy-mm-dd>`.
- Make the order handle derive from your own IDs, so retries and reconciliation are idempotent.

### Track orders

```bash
curl -sS -X POST https://v3.api.hypertrack.com/orders/track \
  -u "$HYPERTRACK_ACCOUNT_ID:$HYPERTRACK_SECRET_KEY" \
  -H 'Content-Type: application/json' \
  -d '{
    "worker_handle": "user-8841",
    "track_mode": "pre_shift",
    "ops_group_handle": "west",
    "orders": [
      {
        "order_handle": "shift-5521-2026-11-03",
        "destination": { "place_handle": "site-sf-ferry-building" },
        "scheduled_at": "2026-11-03T16:00:00Z",
        "expected_service_time": 28800,
        "metadata": { "shift_id": "5521", "client": "acme" }
      }
    ]
  }'
```

Top-level fields:

- `track_mode`, required: `pre_shift` | `on_shift` | `full_shift`. `on_time` and `flex` are deprecated.
- `worker_handle` (or `device_id`): who to track.
- `ops_group_handle`: optional.
- `device_switch_mode`: `login` (default; follows the device the worker last logged into), `closest_to_destination` (for workers with several devices), or `manual`. This is top-level, not per order.

Per-order fields:

- `order_handle` and `destination`, both required.
- `scheduled_at` is the arrival target. Delay risk is measured against it; without it, delay is relative to the first ETA.
- `scheduled_after` is the start of the arrival window.
- `expected_service_time` is in seconds. It's a reference value only; it never auto-completes the order.
- `metadata`: arbitrary JSON for filtering and joins.

Destinations (pick one form):

```json
{ "place_handle": "site-sf-ferry-building" }
```

```json
{ "geometry": { "type": "Point", "coordinates": [-122.393403, 37.795409] }, "radius": 150, "address": "1 Ferry Building, San Francisco, CA" }
```

```json
{
  "geometry": {
    "type": "Polygon",
    "coordinates": [[[-122.3945, 37.7950], [-122.3925, 37.7950], [-122.3925, 37.7960], [-122.3945, 37.7960], [-122.3945, 37.7950]]]
  }
}
```

Coordinates are `[longitude, latitude]`, and polygon rings must close (first point = last point). A swapped pair usually lands in the ocean or on another continent. If your data stores lat/lng, convert it in exactly one helper.

The `201` response is the route: `route_handle`, `embed_url`, and `orders[]`. Each order has `status`, `share_url`, `embed_url`, and timestamps. Store `share_url` (the customer-facing live view) and `embed_url` if you'll show them.

### After tracking

| Need                                    | Call                                                                                                                                                         |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Current state and timeline              | `GET /orders/{order_handle}`: `status`, `started_at`, `arrived_at`, `exited_at`, `completed_at`, `risks`, `tracking_rate`, `actual_service_time`, `timeline` |
| Change destination, time, or metadata   | `PATCH /orders/{order_handle}` with `destination`, `scheduled_at`, `scheduled_after`, `expected_service_time`, `metadata`, …                                 |
| Move the order to another worker        | `POST /orders/{order_handle}/reassign` with `{"worker_handle": "…"}`                                                                                         |
| Reschedule a planned order              | `POST /orders/{order_handle}/reschedule` with `{"scheduled_at": "…"}`. If the order was already dispatched, this cancels it and recreates it unplanned.      |
| Record a business event on the timeline | `POST /orders/{order_handle}/events` with `{"events": [{"type": "…", "recorded_at": "…", "metadata": {…}}]}`                                                 |
| Finish                                  | `POST /orders/{order_handle}/complete` or `/cancel` (empty body). Set any final metadata with `PATCH` first.                                                 |
| Webhooks sent for an order (debugging)  | `GET /orders/{order_handle}/webhooks`: each event, plus your endpoint's `delivery_http_status` and `retry_count`                                             |
| Search                                  | `GET /orders/` with `worker_handle`, `status`, `track_mode`, `place_handle`, `ops_group_handle`, date ranges, `limit`, and `pagination_token` for paging     |

Ground-truth labels for no-show / on-time models go in metadata through `PATCH`: `{"metadata": {"ht_on_time_arrival": true, "ht_worked_shift": true}}`.

### Scheduling start and end

- Run a scheduler (cron, job queue) that calls `/orders/track` at `scheduled_at − lead time` and completes the order at the shift's end, unless a worker action or your system ends it earlier.
- On shift cancellation in your system, cancel the HyperTrack order in the same transaction or job.
- Reconcile periodically: list `GET /orders/?status=ongoing` and complete or cancel anything your system considers finished.

## Places

Create recurring destinations once, then reference them by `place_handle`:

```bash
curl -sS -X POST https://v3.api.hypertrack.com/places/v1/ \
  -u "$HYPERTRACK_ACCOUNT_ID:$HYPERTRACK_SECRET_KEY" \
  -H 'Content-Type: application/json' \
  -d '{
    "place_handle": "site-sf-ferry-building",
    "name": "Ferry Building",
    "geometry": { "type": "Point", "coordinates": [-122.393403, 37.795409] },
    "radius": 150,
    "address": "1 Ferry Building, San Francisco, CA 94111",
    "metadata": { "client": "acme" }
  }'
```

- With only an `address`, HyperTrack geocodes it to an approximate polygon. Provide geometry when you have it.
- Also available: `GET /places/v1/` (filters: `place_handles`, `search_term`, `lat`/`lon`/`radius`, …), `GET`/`PATCH`/`DELETE /places/v1/{place_handle}`.
- HyperTrack learns tighter boundaries from real visits. Review suggestions in the dashboard, or with `GET /places/v1/{place_handle}/suggestions/` and `POST …/suggestions/{suggestion_id}/apply`.
- Places also support `checkins`, `parkings`, `timings`, and `expected_service_time`. See the spec.

## Workers

- Workers are created automatically when the app sets the worker handle. Use `POST /workers/` to pre-provision one with `worker_handle` (required), `name`, `profile` (arbitrary JSON), `ops_group_handle`, `schedule`, `home`, or `product_types`. The app still has to set the same handle.
- `GET /workers/{worker_handle}` returns the linked device, `device_status`, last `location`, `location_permission`, `work_status`, and `battery`. Check it first when a worker "isn't tracking".
- `PATCH /workers/{worker_handle}` updates a worker. `DELETE` removes one (`POST …/undelete` restores it).
- Ops groups: `POST /workers/ops-groups/` with `{"ops_group_handle", "ops_group_label", "timezone"}`.
- `POST /workers/{worker_handle}/work_status` with `{"tracking": bool, "available": bool}` is the low-level manual switch. Prefer orders for tracking. Server-side `available` doesn't currently reach the device (see `mobile.md` § Availability).

## Nearby search

Find available workers near a destination (for backfill or on-demand assignment):

```bash
curl -sS -X POST https://v3.api.hypertrack.com/nearby/v4 \
  -u "$HYPERTRACK_ACCOUNT_ID:$HYPERTRACK_SECRET_KEY" \
  -H 'Content-Type: application/json' \
  -d '{
    "order": { "destination": { "geometry": { "type": "Point", "coordinates": [-122.393403, 37.795409] } } },
    "search_type": "region",
    "search_filter": { "search_radius": 16000, "worker_profile": { "team": "north" } },
    "limit": 20
  }'
```

- `search_type`: `region` sorts by straight-line distance. `eta` sorts by drive time with traffic; use `worker_list` to estimate specific workers.
- Results are capped at 1000 workers. `search_radius` defaults to and maxes out at 160934 m (100 miles).
- Only workers who are available appear, and only with a fresh location if availability was set on the device.
- To rank candidates for an existing order: `GET /orders/{order_handle}/candidate_workers`.

## Live views and sharing

- `share_url` (per order): customer-facing live tracking link.
- `embed_url` (per order and per route): ops view that works in an iframe without login. Fine for internal tools and development.
- **Secure order embed for end users:** `POST /oauth/embed-token` (basic auth) with `{"grant_type": "client_credentials", "embed_url": "https://embed.hypertrack.com/orders/<order_handle>?fulfillment_attempt=0"}`. Use the returned `secure_embed_url` unchanged as the iframe `src`. It's short-lived and scoped to that order. Add `show-visits-only=true` for visit-only views. The order must exist and have a device.
- **Account-wide ops views:** get an OAuth token with a narrow scope (`read.embed.orders`, `read.embed.devices`) and load `https://embed.hypertrack.com/views/orders?token=<access_token>`. Mint it server-side and never expose the secret.
- Don't set `Referrer-Policy: same-origin` on pages that embed HyperTrack iframes. In a sandboxed iframe, allow `allow-scripts allow-same-origin`.
