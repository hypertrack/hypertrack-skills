# iOS SDK Integration

## Requirements

- iOS 12+
- CPU: arm64, arm64e
- Simulator: arm64, x86_64

## Add SDK dependency

### Swift Package Manager (recommended)

File → Add Package Dependencies → enter:

```
https://github.com/hypertrack/sdk-ios
```

### CocoaPods

```ruby
# Podfile
platform :ios, '12.0'
inhibit_all_warnings!

target 'YourApp' do
  use_frameworks!
  pod 'HyperTrack', '<version>'
end
```

Then run `pod install` and open the `.xcworkspace`.

## Enable Background Modes

In your target's Signing & Capabilities → Background Modes, enable:

- **Location updates**
- **Remote notifications**

Also ensure **Push Notifications** capability is added in the same tab.

> If Background Modes or Push Notifications are missing, tracking will not work when the app is backgrounded or when orders are created server-side.

## Add purpose strings

In `Info.plist`, add these keys with user-facing descriptions explaining why location is needed:

| Key | Required | Notes |
|-----|----------|-------|
| `NSLocationAlwaysAndWhenInUseUsageDescription` | Yes | Must request "Always" for reliable tracking |
| `NSLocationWhenInUseUsageDescription` | Yes | Shown first before Always prompt |
| `NSMotionUsageDescription` | Recommended | Improves activity detection in timeline |

The purpose strings should explain the value to the worker (e.g., "Location is used during your shifts to track arrival times and provide accurate shift records.").

## Set up silent push notifications

HyperTrack uses silent push notifications to start/stop tracking when orders are created or completed server-side. **This is mandatory for remote tracking to work.**

### 1. Enable push notifications

Follow Apple's [APNs documentation](https://developer.apple.com/documentation/usernotifications/registering_your_app_with_apns).

### 2. Get your APNs Auth Key

Go to [Apple Developer → Keys](https://developer.apple.com/account/resources/authkeys/list):
- Create a new key with Apple Push Notifications service (APNs) enabled
- Download the `.p8` file (format: `AuthKey_KEYID.p8`)
- Note your **Key ID** and **Team ID**

### 3. Upload to HyperTrack dashboard

Go to [Setup page](https://dashboard.hypertrack.com/setup):
- Upload the `.p8` Auth Key file
- Enter your Team ID

## Set the publishable key

In `Info.plist`, add:

| Key | Type | Value |
|-----|------|-------|
| `HyperTrackPublishableKey` | String | Your publishable key from the Setup page |

## Set worker handle

On login or app launch, link the device to your user:

```swift
HyperTrack.workerHandle = "your_user_id"
```

On logout, clear it:

```swift
HyperTrack.workerHandle = ""
```

> Setting worker_handle creates a worker in HyperTrack if one doesn't exist. Clearing it disconnects the device from the worker.

## Set name and metadata (optional)

```swift
HyperTrack.name = "Jane Smith"
HyperTrack.metadata = [
    "department": "nursing",
    "skills": ["ICU", "ER"],
    "home_address": "123 Main St"
]
```

Metadata appears in dashboard, APIs, and webhooks. Use it for filtering and enrichment.

## Grant permissions

The app must have **Always** location permission for reliable tracking.

Manual grant path: Settings → Privacy → Location Services → YourApp → Allow Location Access → **Always**

Also verify:
- **Location Services** toggle is on
- **Precise Location** toggle is on

### Requesting permissions in code

Use `CLLocationManager.requestAlwaysAuthorization()`. iOS will first show "When In Use" and later prompt for "Always" — follow Apple's progressive authorization pattern.

> If only "When In Use" is granted, tracking will stop when the app is backgrounded.

## Handle errors

Subscribe to errors to catch permission issues, tracking blockers, etc.:

```swift
var errorsCancellable: HyperTrack.Cancellable? = nil

errorsCancellable = HyperTrack.subscribeToErrors { errors in
    for error in errors {
        switch error {
        case .location(.permissions(.denied)):
            // Prompt user to enable location permissions
        case .location(.permissions(.insufficientForBackground)):
            // "Always" permission not granted
        case .location(.permissions(.reducedAccuracy)):
            // Precise location not enabled
        case .location(.servicesDisabled):
            // Location Services turned off system-wide
        default:
            print("HyperTrack error: \(error)")
        }
    }
}
```

Or query synchronously when needed:

```swift
for error in HyperTrack.errors {
    // handle each error
}
```

See [Error API Reference](https://hypertrack.github.io/sdk-ios/) for the full error list.

## Add geotags (optional)

For clock-in/out events on order timelines:

```swift
// Clock in
let result = HyperTrack.addGeotag(
    orderHandle: "shift-123",
    orderStatus: .clockIn,
    metadata: ["facility": "Building A"]
)

// Clock out
let result = HyperTrack.addGeotag(
    orderHandle: "shift-123",
    orderStatus: .clockOut,
    metadata: [:]
)

// Custom event
let result = HyperTrack.addGeotag(
    orderHandle: "shift-123",
    orderStatus: .custom("break_start"),
    metadata: [:]
)
```

## Worker availability (optional)

For nearby search to include this worker:

```swift
HyperTrack.isAvailable = true   // Worker ready for assignments
HyperTrack.isAvailable = false  // Worker off-duty
```

## Verification checklist

After completing SDK setup:

- [ ] App builds and runs without SDK-related errors
- [ ] `HyperTrack.workerHandle` is set on login
- [ ] Location permission is "Always" with Precise Location on
- [ ] Background Modes enabled (Location updates + Remote notifications)
- [ ] Push Notifications capability added
- [ ] APNs key uploaded to HyperTrack dashboard
- [ ] `HyperTrack.errors` returns an empty set
- [ ] Worker appears on [HyperTrack dashboard](https://dashboard.hypertrack.com)

## References

- [HyperTrack iOS SDK API Reference](https://hypertrack.github.io/sdk-ios/)
- [Quickstart app](https://github.com/hypertrack/quickstart-ios)
- [Install guide](https://hypertrack.com/docs/install-sdk-ios)
