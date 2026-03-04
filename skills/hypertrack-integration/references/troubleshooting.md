# Troubleshooting

Common issues, diagnostic steps, and fixes for HyperTrack integrations.

---

## Credential issues

### "401 Authentication error" from API

**Cause:** Invalid or missing AccountID/SecretKey.

**Diagnose:**
```bash
# Test credentials
curl -s -o /dev/null -w '%{http_code}' \
  -u '{AccountID}:{SecretKey}' \
  https://v3.api.hypertrack.com/workers/
```

**Fix:**
- Verify AccountID and SecretKey from [Setup page](https://dashboard.hypertrack.com/setup)
- Ensure Basic auth header is `base64(AccountID:SecretKey)` — not `base64(AccountID)` + `base64(SecretKey)` separately
- Check for trailing whitespace or newlines in credential strings
- Verify you're using SecretKey (not Publishable Key) for API calls

### Publishable key not working in SDK

**Cause:** Wrong key type or misconfigured.

**Fix:**
- Use the **Publishable Key** (not SecretKey) in the mobile SDK
- iOS: verify `HyperTrackPublishableKey` key exists in `Info.plist` with type `String`
- Android: verify `<meta-data android:name="HyperTrackPublishableKey" android:value="..."/>` in `AndroidManifest.xml`
- Ensure no extra quotes or whitespace around the value

---

## SDK not tracking

### Worker doesn't appear on dashboard

**Diagnostic steps (in order):**

1. **Is `worker_handle` set?**
   - Verify `HyperTrack.workerHandle` (or `.setWorkerHandle()`) is called after login
   - It must be a non-empty string

2. **Are permissions granted?**
   - Check `HyperTrack.errors` — look for permission-related errors
   - iOS: Must be "Always" + Precise Location
   - Android: Must have fine location + background location (API 30+)

3. **Is the publishable key correct?**
   - Cross-check with dashboard Setup page

4. **Are silent push notifications configured?**
   - iOS: APNs key uploaded to dashboard + Push Notifications capability + Background Modes
   - Android: FCM service account key uploaded to dashboard + Firebase configured in app

5. **Is there an active order or tracking intent?**
   - Remote tracking only starts when an order exists or `work_status.tracking` is `true`
   - For testing: create an order via API for the worker, then check if tracking starts

### Tracking starts but stops after app is backgrounded

**Cause (iOS):** Missing Background Modes or "Always" location permission.

**Fix:**
- Enable Background Modes → Location updates + Remote notifications
- Ensure location permission is "Always", not "When In Use"
- Verify `NSLocationAlwaysAndWhenInUseUsageDescription` is in Info.plist

**Cause (Android):** Battery optimization killing the app.

**Fix:**
- Whitelist app from battery saver (device-specific, see `sdk-android.md`)
- Grant `ACCESS_BACKGROUND_LOCATION` permission (Android 11+)
- Check `HyperTrack.errors` for "Tracking services terminated" or "SDK killed by user"

### Tracking won't start when order is created server-side

**Cause:** Silent push notifications not reaching the device.

**Diagnostic:**
1. Create an order via API for the worker
2. Check dashboard — does the order show up?
3. If order exists but device isn't tracking, push isn't reaching the device

**Fix:**
- **iOS:** Verify APNs key is uploaded (not expired), Push Notifications capability is enabled, and Background Modes → Remote notifications is on
- **Android:** Verify FCM service account key is uploaded, `google-services.json` is in the app, and `push-service-firebase` dependency is included
- As a workaround, opening the app will trigger sync and start tracking

---

## Order and destination issues

### Order created at wrong location

**Cause:** Coordinates in wrong order.

**Fix:** GeoJSON uses `[longitude, latitude]`:
```json
"coordinates": [-122.394, 37.793]
```
NOT `[37.793, -122.394]`. If your place ends up in the ocean or a different continent, coordinates are swapped.

### "422 Validation error" when creating order

**Common causes:**
- Missing required field (`order_handle` or `destination`)
- `track_mode` not one of: `pre_shift`, `on_shift`, `full_shift`
- Invalid destination geometry (malformed GeoJSON, polygon not closed)
- `worker_handle` doesn't match any known worker or device
- Duplicate `order_handle` for an active order (409 Conflict)

**Diagnose:** The 422 response body contains validation error details. Check it:
```bash
curl -v -X POST https://v3.api.hypertrack.com/orders/track \
  -u '{AccountID}:{SecretKey}' \
  -H 'Content-Type: application/json' \
  -d '{ ... }'
```

### Worker arrives but no geofence entry detected

**Cause:** Destination geofence too small or inaccurate.

**Fix:**
- Increase `radius` (try 200m for testing)
- Verify destination coordinates are correct
- Use HyperTrack Places with auto-improving boundaries
- Check if the building entrance vs GPS position has significant offset

### Order never stops tracking

**Cause:** Order was never completed or cancelled.

**Fix:**
- Call `POST /orders/{order_handle}/complete` or `POST /orders/{order_handle}/cancel`
- For recurring shifts, set up a cron to complete orders at shift end time
- Check dashboard for orphaned active orders

---

## Permission issues

### iOS: "When In Use" instead of "Always"

iOS shows "When In Use" first, then may prompt for "Always" later. If the user denies the upgrade:

1. The app cannot programmatically re-request "Always" permission
2. Guide users to: Settings → Privacy → Location Services → YourApp → Always

### Android: Background location not granted

On Android 11+ (API 30+), background location is a separate permission:
1. First grant fine location
2. Then explicitly request `ACCESS_BACKGROUND_LOCATION`
3. Some devices show "Allow all the time" only in Settings, not in the runtime dialog

### Permissions revoked after granting

Users can revoke permissions at any time. Subscribe to errors in the SDK:
```
HyperTrack.subscribeToErrors { errors -> ... }
```

Check on every app launch or foreground resume.

---

## Webhook issues

### Webhooks not arriving

1. **Is the URL configured?** Check [Setup page](https://dashboard.hypertrack.com/setup)
2. **Is the endpoint reachable?** Test with `curl -X POST https://your-endpoint.com/webhooks`
3. **Is it HTTPS?** HTTP endpoints are not supported
4. **Is it responding within 10 seconds?** Slow responses cause timeouts
5. **Is it returning 2xx?** Non-2xx (except 4xx) triggers retries

### Webhooks arriving out of order

Expected behavior — network conditions can cause this. Always use `recorded_at` for ordering, not receive time.

### Duplicate webhooks

Retries reuse the same `x-amz-sns-message-id`. Store processed message IDs and skip duplicates.

---

## Outage codes

When tracking is interrupted, HyperTrack reports the reason. Common codes and categories:

### Behavioral (user action)
- Location permissions denied/revoked
- App deleted/uninstalled
- Location services turned off

### Adversarial (fraud)
- Location mocking detected
- Time offset manipulation (device clock changed)

### Operating System
- App terminated (low memory)
- System reboot
- OS update
- Excessive resource usage

### Sporadic (environmental)
- Low battery
- Battery saver active
- GPS unavailable (indoors, tunnel)

### Reachability
- No internet connectivity
- Push notification token missing/invalid

View outage details in the order timeline on the dashboard or via the GET order timeline API.

---

## Quick diagnostic checklist

Use this to quickly narrow down integration issues:

```
1. API credentials work?
   curl -s -u 'ID:KEY' https://v3.api.hypertrack.com/workers/ → 200?
   YES → continue | NO → fix credentials

2. SDK errors empty?
   HyperTrack.errors → []?
   YES → continue | NO → fix reported errors

3. Worker appears on dashboard?
   YES → continue | NO → check worker_handle + publishable key

4. Creating an order starts tracking?
   POST /orders/track → device starts moving on dashboard?
   YES → continue | NO → check silent push notifications

5. Webhooks arriving?
   Order events hitting your endpoint?
   YES → integration working | NO → check webhook URL + endpoint

6. Completing order stops tracking?
   POST /orders/{handle}/complete → tracking stops?
   YES → done | NO → check push notifications + any remaining active orders
```

---

## Getting help

- HyperTrack Slack community: instant responses
- Email: help@hypertrack.com
- HyperTrack mobile team offers joint app/SDK integration reviews
- Online FAQ: https://hypertrack.com/faq
