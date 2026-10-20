#!/usr/bin/env python3
"""HyperTrack verification CLI for coding agents (Python 3.9+, stdlib only).

Credentials come from HYPERTRACK_ACCOUNT_ID and HYPERTRACK_SECRET_KEY
(the same variables the HyperTrack MCP server uses). Never pass them as arguments.
"""

import argparse
import base64
import hashlib
import hmac
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

API = os.environ.get("HYPERTRACK_API_BASE_URL", "https://v3.api.hypertrack.com").rstrip("/")


def die(message):
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


def credentials():
    account_id = os.environ.get("HYPERTRACK_ACCOUNT_ID", "").strip()
    secret_key = os.environ.get("HYPERTRACK_SECRET_KEY", "").strip()
    if not account_id or not secret_key:
        die("set HYPERTRACK_ACCOUNT_ID and HYPERTRACK_SECRET_KEY (dashboard Setup page) in the environment")
    return account_id, secret_key


def call(method, path, body=None, query=None):
    account_id, secret_key = credentials()
    url = API + path
    if query:
        url += "?" + urllib.parse.urlencode({k: v for k, v in query.items() if v is not None})
    token = base64.b64encode(f"{account_id}:{secret_key}".encode()).decode()
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Authorization", f"Basic {token}")
    request.add_header("Accept", "application/json")
    if data is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read()
    except urllib.error.HTTPError as error:
        raw = error.read()
        try:
            problem = json.loads(raw)
            detail = " | ".join(str(problem.get(k)) for k in ("code", "title", "detail") if problem.get(k))
            if problem.get("invalid_params"):
                detail += f" | invalid_params={json.dumps(problem['invalid_params'])}"
        except ValueError:
            detail = raw.decode(errors="replace")[:500]
        die(f"{method} {path} -> HTTP {error.code}: {detail}")
    except urllib.error.URLError as error:
        die(f"{method} {path} -> {error.reason}")
    return json.loads(raw) if raw else {}


def handle(value):
    return urllib.parse.quote(value, safe="")


def pick(obj, keys):
    return {k: obj.get(k) for k in keys if obj.get(k) is not None}


def show(value):
    print(json.dumps(value, indent=2, sort_keys=False, default=str))


def cmd_check(args):
    result = call("GET", "/workers/", query={"limit": 1})
    workers = result.get("workers") or []
    print(f"OK: credentials valid for {API} (sample worker: {workers[0]['worker_handle'] if workers else 'none yet'})")


def cmd_worker(args):
    worker = call("GET", f"/workers/{handle(args.worker_handle)}")
    if args.json:
        return show(worker)
    summary = pick(
        worker,
        [
            "worker_handle",
            "name",
            "ops_group_handle",
            "device_id",
            "device_status",
            "work_status",
            "location_permission",
            "location",
            "battery",
            "device_info",
        ],
    )
    devices = worker.get("devices") or []
    if devices:
        summary["devices"] = [pick(d, ["device_id", "linked_at", "unlinked_at", "is_active"]) or d for d in devices]
    show(summary)


def cmd_track(args):
    if args.place:
        destination = {"place_handle": args.place}
    else:
        if args.lat is None or args.lon is None:
            die("pass --lat and --lon, or --place")
        destination = {
            "geometry": {"type": "Point", "coordinates": [args.lon, args.lat]},  # GeoJSON: [lon, lat]
            "radius": args.radius,
        }
    order = {
        "order_handle": args.order or "agent-test-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "destination": destination,
        "metadata": {"created_by": "hypertrack-skill ht.py"},
    }
    if args.scheduled_at:
        order["scheduled_at"] = args.scheduled_at
    if args.expected_service_time:
        order["expected_service_time"] = args.expected_service_time
    body = {"worker_handle": args.worker_handle, "track_mode": args.mode, "orders": [order]}
    if args.device_switch_mode:
        body["device_switch_mode"] = args.device_switch_mode
    result = call("POST", "/orders/track", body)
    if args.json:
        return show(result)
    summary = pick(result, ["route_handle", "status", "device_id", "embed_url"])
    summary["orders"] = [pick(o, ["order_handle", "status", "share_url", "embed_url"]) for o in result.get("orders") or []]
    show(summary)
    print(f"\nNext: python3 {sys.argv[0]} order {order['order_handle']}  (complete or cancel it when done)")


def cmd_order(args):
    order = call("GET", f"/orders/{handle(args.order_handle)}")
    if args.json:
        return show(order)
    summary = pick(
        order,
        [
            "order_handle",
            "status",
            "track_mode",
            "worker_handle",
            "device_id",
            "place_handle",
            "created_at",
            "started_at",
            "scheduled_at",
            "arrived_at",
            "exited_at",
            "completed_at",
            "cancelled_at",
            "risk_status",
            "risks",
            "tracking_rate",
            "time_to_first_location",
            "actual_service_time",
            "share_url",
            "embed_url",
        ],
    )
    destination = order.get("destination") or {}
    summary["destination"] = pick(destination, ["place_handle", "address", "geometry", "radius"])
    timeline = order.get("timeline") or []
    if timeline:
        summary["timeline"] = [
            pick(
                event,
                ["type", "recorded_at", "recorded_at_start", "recorded_at_end", "outage_code", "is_ongoing"],
            )
            for event in timeline[-args.events :]
        ]
    show(summary)


def cmd_webhooks(args):
    events, token = [], None
    while True:
        result = call(
            "GET",
            f"/orders/{handle(args.order_handle)}/webhooks",
            query={"pagination_token": token, "limit": 100},
        )
        events.extend(result.get("webhooks") or [])  # the spec allows null
        token = result.get("pagination_token")
        if not token or len(events) >= args.max:
            break
    if args.json:
        return show(events)
    if not events:
        print("No webhooks recorded for this order yet.")
        return
    for event in sorted(events, key=lambda e: e.get("recorded_at") or ""):
        data = event.get("data") or {}
        status = event.get("delivery_http_status")
        retries = event.get("retry_count")
        line = f"{event.get('recorded_at')}  {event.get('type')}:{data.get('value')}"
        line += f"  http={status if status is not None else '-'}"
        if retries:
            line += f" retries={retries}"
        print(line)
        if args.verbose and event.get("delivery_http_response_text"):
            print(f"    response: {event['delivery_http_response_text'][:300]}")


def cmd_finish(args):
    result = call("POST", f"/orders/{handle(args.order_handle)}/{args.command}", {})
    show(result if args.json else pick(result, ["order_handle", "status", "completed_at", "cancelled_at"]))


def cmd_sign(args):
    _, secret_key = credentials()
    with open(args.body_file, "rb") as body:
        print(hmac.new(secret_key.encode(), body.read(), hashlib.sha1).hexdigest())


def main():
    parser = argparse.ArgumentParser(
        description="Verify a HyperTrack integration. Uses HYPERTRACK_ACCOUNT_ID / HYPERTRACK_SECRET_KEY.",
    )
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="print the raw API response")
    sub = parser.add_subparsers(dest="command", required=True)

    def add(name, help_text):
        return sub.add_parser(name, help=help_text, parents=[common])

    add("check", "verify credentials").set_defaults(func=cmd_check)

    p = add("worker", "worker status: device, permissions, work status, last location")
    p.add_argument("worker_handle")
    p.set_defaults(func=cmd_worker)

    p = add("track", "create and track a TEST order (starts tracking the worker's device)")
    p.add_argument("worker_handle")
    p.add_argument("--lat", type=float, help="destination latitude")
    p.add_argument("--lon", type=float, help="destination longitude")
    p.add_argument("--radius", type=int, default=150, help="geofence radius in meters (default 150)")
    p.add_argument("--place", help="use an existing place_handle as the destination")
    p.add_argument("--mode", default="on_shift", choices=["pre_shift", "on_shift", "full_shift"])
    p.add_argument("--order", help="order_handle (default: agent-test-<timestamp>)")
    p.add_argument("--scheduled-at", help="ISO 8601 arrival target, e.g. 2026-11-03T16:00:00Z")
    p.add_argument("--expected-service-time", type=int, help="seconds")
    p.add_argument("--device-switch-mode", choices=["login", "closest_to_destination", "manual"])
    p.set_defaults(func=cmd_track)

    p = add("order", "order status, timestamps, risks, latest timeline events")
    p.add_argument("order_handle")
    p.add_argument("--events", type=int, default=10, help="timeline events to show (default 10)")
    p.set_defaults(func=cmd_order)

    p = add("webhooks", "webhooks sent for an order, with your endpoint's HTTP status")
    p.add_argument("order_handle")
    p.add_argument("--max", type=int, default=500)
    p.add_argument("-v", "--verbose", action="store_true", help="include your endpoint's response text")
    p.set_defaults(func=cmd_webhooks)

    for name in ("complete", "cancel"):
        p = add(name, f"{name} an order")
        p.add_argument("order_handle")
        p.set_defaults(func=cmd_finish)

    p = add("sign", "print the expected x-hypertrack-signature for a raw webhook body file")
    p.add_argument("body_file")
    p.set_defaults(func=cmd_sign)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
