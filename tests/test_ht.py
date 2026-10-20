"""ht.py against a local mock of the HyperTrack API (no real account)."""

import hashlib
import hmac
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

HT = Path(__file__).resolve().parent.parent / "skills/hypertrack-integration/scripts/ht.py"


class MockAPI(BaseHTTPRequestHandler):
    requests = []
    webhook_pages = {}

    def log_message(self, *args):
        pass

    def send_json(self, status, body):
        raw = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        MockAPI.requests.append(("GET", self.path, self.headers.get("Authorization"), None))
        if self.path.startswith("/workers/?"):
            return self.send_json(200, {"workers": None, "pagination_token": None})
        if self.path.startswith("/workers/james%40co.com"):
            return self.send_json(200, {"worker_handle": "james@co.com", "device_id": "D1", "devices": None})
        if self.path.startswith("/workers/"):
            return self.send_json(404, {"status": 404, "code": "worker_not_found", "title": "Not found", "detail": "no worker"})
        if self.path.startswith("/orders/o1/webhooks"):
            token = "p2" if "pagination_token=p2" in self.path else None
            return self.send_json(200, MockAPI.webhook_pages[token])
        if self.path.startswith("/orders/o1"):
            return self.send_json(200, {"order_handle": "o1", "status": "ongoing", "destination": None, "timeline": None})
        return self.send_json(404, {"code": "not_found"})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        MockAPI.requests.append(("POST", self.path, self.headers.get("Authorization"), body))
        if self.path == "/orders/track":
            if body["orders"][0]["order_handle"] == "dup":
                return self.send_json(409, {"status": 409, "code": "duplicate_resource", "title": "Duplicate", "detail": "exists"})
            return self.send_json(201, {"route_handle": "r1", "orders": None})
        if self.path in ("/orders/o1/complete", "/orders/o1/cancel"):
            return self.send_json(200, {"order_handle": "o1", "status": "completed"})
        return self.send_json(400, {"code": "bad_request"})


class HtTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), MockAPI)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.env = dict(
            os.environ,
            HYPERTRACK_API_BASE_URL=f"http://127.0.0.1:{cls.server.server_port}",
            HYPERTRACK_ACCOUNT_ID="acc",
            HYPERTRACK_SECRET_KEY="sec",
        )

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        MockAPI.requests.clear()

    def ht(self, *args, env=None):
        return subprocess.run([sys.executable, str(HT), *args], env=env or self.env, capture_output=True, text=True)

    def test_check_handles_null_worker_list(self):
        result = self.ht("check")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("credentials valid", result.stdout)
        self.assertEqual(MockAPI.requests[0][2], "Basic YWNjOnNlYw==")

    def test_missing_credentials_fail_without_request(self):
        env = dict(self.env)
        env.pop("HYPERTRACK_SECRET_KEY")
        result = self.ht("check", env=env)
        self.assertEqual(result.returncode, 1)
        self.assertIn("HYPERTRACK_SECRET_KEY", result.stderr)
        self.assertEqual(MockAPI.requests, [])

    def test_worker_handle_is_url_encoded(self):
        result = self.ht("worker", "james@co.com")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(MockAPI.requests[0][1].split("?")[0], "/workers/james%40co.com")

    def test_api_error_reports_problem_details(self):
        result = self.ht("worker", "nobody")
        self.assertEqual(result.returncode, 1)
        self.assertIn("HTTP 404: worker_not_found", result.stderr)

    def test_track_sends_geojson_longitude_first(self):
        result = self.ht("track", "james@co.com", "--lat", "37.795409", "--lon", "-122.393403", "--order", "o1")
        self.assertEqual(result.returncode, 0, result.stderr)
        body = MockAPI.requests[0][3]
        self.assertEqual(body["track_mode"], "on_shift")
        self.assertEqual(body["orders"][0]["destination"]["geometry"]["coordinates"], [-122.393403, 37.795409])

    def test_track_conflict_fails(self):
        result = self.ht("track", "james@co.com", "--lat", "1", "--lon", "2", "--order", "dup")
        self.assertEqual(result.returncode, 1)
        self.assertIn("duplicate_resource", result.stderr)

    def test_track_requires_destination(self):
        result = self.ht("track", "james@co.com")
        self.assertEqual(result.returncode, 1)
        self.assertIn("--lat", result.stderr)

    def test_order_handles_null_fields(self):
        result = self.ht("order", "o1")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_webhooks_follow_pagination_and_sort(self):
        MockAPI.webhook_pages = {
            None: {"webhooks": [{"recorded_at": "2026-01-01T00:00:02Z", "type": "order", "data": {"value": "arrived"},
                                 "delivery_http_status": 500, "retry_count": 3}], "pagination_token": "p2"},
            "p2": {"webhooks": [{"recorded_at": "2026-01-01T00:00:01Z", "type": "order", "data": {"value": "started"},
                                 "delivery_http_status": 200}], "pagination_token": None},
        }
        result = self.ht("webhooks", "o1")
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.strip().splitlines()
        self.assertIn("order:started  http=200", lines[0])
        self.assertIn("order:arrived  http=500 retries=3", lines[1])

    def test_webhooks_null_list_is_empty(self):
        MockAPI.webhook_pages = {None: {"webhooks": None, "pagination_token": None}}
        result = self.ht("webhooks", "o1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("No webhooks", result.stdout)

    def test_complete_and_cancel(self):
        for command in ("complete", "cancel"):
            result = self.ht(command, "o1")
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([r[1] for r in MockAPI.requests], ["/orders/o1/complete", "/orders/o1/cancel"])

    def test_sign_matches_hmac_sha1_of_raw_body(self):
        body = b'[{"type":"order","data":{"value":"arrived"}}]'
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as handle:
            handle.write(body)
        try:
            result = self.ht("sign", handle.name)
        finally:
            os.unlink(handle.name)
        self.assertEqual(result.stdout.strip(), hmac.new(b"sec", body, hashlib.sha1).hexdigest())


if __name__ == "__main__":
    unittest.main()
