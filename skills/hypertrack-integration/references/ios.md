# iOS SDK

Requires iOS 12+. Code blocks here typecheck against the HyperTrack iOS SDK. If something doesn't compile against a newer SDK, check the [SDK reference](https://hypertrack.github.io/mobile/sdk-ios/latest/documentation/hypertrack/hypertrack/) and `CHANGELOG.md` in `hypertrack/sdk-ios`.

## Install

- **Swift Package Manager:** add `https://github.com/hypertrack/sdk-ios`, product `HyperTrack`.
- **CocoaPods:** `pod 'HyperTrack', '<version>'` with `use_frameworks!` and `platform :ios, '12.0'` or higher, then `pod install` and open the `.xcworkspace`.

Latest version: `tag_name` from `https://api.github.com/repos/hypertrack/sdk-ios/releases/latest`.

## Project configuration

In the target's Signing & Capabilities:

- **Background Modes:** Location updates, Remote notifications
- **Push Notifications** (adds the `aps-environment` entitlement)

`Info.plist`:

```xml
<key>HyperTrackPublishableKey</key>
<string>YOUR_PUBLISHABLE_KEY</string>
<key>NSLocationWhenInUseUsageDescription</key>
<string>Your location is used during shifts to record arrival times and time on site.</string>
<key>NSLocationAlwaysAndWhenInUseUsageDescription</key>
<string>Your location is used during shifts, even when the app is closed, to record arrival times and time on site.</string>
<key>NSMotionUsageDescription</key>
<string>Motion data improves activity detection in your shift timeline.</string>
<key>UIBackgroundModes</key>
<array>
    <string>location</string>
    <string>remote-notification</string>
</array>
```

Purpose strings are mandatory. Write them for the worker and say why tracking helps them (App Store review reads them). Motion permission is optional but improves activity detection.

## Silent push (APNs)

1. Apple Developer → Keys → create a key with APNs enabled. Download the `AuthKey_<KEYID>.p8` file and note the Team ID.
2. On the dashboard [Setup page](https://dashboard.hypertrack.com/setup), upload the `.p8` and enter the Team ID.
3. That's all the code you need. By default the SDK swizzles the `AppDelegate` push callbacks.

**If swizzling conflicts** with another library (common with Flutter + Firebase), set the Boolean `HyperTrackSwizzlingEnabled` to `NO` in `Info.plist` and forward these calls yourself:

```swift
import HyperTrack
import UIKit

class AppDelegate: UIResponder, UIApplicationDelegate {
  func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    HyperTrack.didFinishLaunchingWithOptions(launchOptions)
    return true
  }

  func application(_ application: UIApplication, didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {
    HyperTrack.didRegisterForRemoteNotificationsWithDeviceToken(deviceToken)
  }

  func application(_ application: UIApplication, didFailToRegisterForRemoteNotificationsWithError error: Error) {
    HyperTrack.didFailToRegisterForRemoteNotificationsWithError(error)
  }

  func application(
    _ application: UIApplication,
    didReceiveRemoteNotification userInfo: [AnyHashable: Any],
    fetchCompletionHandler completionHandler: @escaping (UIBackgroundFetchResult) -> Void
  ) {
    HyperTrack.didReceiveRemoteNotification(userInfo, fetchCompletionHandler: completionHandler)
  }
}
```

In a subclassed delegate (e.g. `FlutterAppDelegate`), call `super` in each override as well.

## Worker handle, name, metadata

```swift
import HyperTrack

func onLogin(userID: String, displayName: String) {
  HyperTrack.workerHandle = userID
  HyperTrack.name = displayName
  HyperTrack.metadata = ["team": "north", "vehicle": "van"]
}

func onLogout() {
  HyperTrack.workerHandle = ""
}
```

## Location permissions (When In Use first, then Always)

```swift
import CoreLocation
import UIKit

final class LocationPermissions: NSObject, CLLocationManagerDelegate {
  private let manager = CLLocationManager()

  override init() {
    super.init()
    manager.delegate = self
  }

  /// Call from a foreground screen before the worker can start work.
  func request() {
    switch manager.authorizationStatus {
    case .notDetermined:
      manager.requestWhenInUseAuthorization()
    case .authorizedWhenInUse:
      manager.requestAlwaysAuthorization()
    case .denied, .restricted:
      UIApplication.shared.open(URL(string: UIApplication.openSettingsURLString)!)
    default:
      break
    }
  }

  func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
    if manager.authorizationStatus == .authorizedWhenInUse {
      manager.requestAlwaysAuthorization()
    }
  }
}
```

`authorizationStatus` on the manager instance requires iOS 14+. For an older deployment target, use `CLLocationManager.authorizationStatus()`.

## Errors

The error type is nested: `.permissions(.location(...))` for permission problems, `.location(...)` for location-service problems.

```swift
import HyperTrack

// Retain the cancellable for as long as the screen needs updates.
var errorsCancellable: HyperTrack.Cancellable?

func observeErrors() {
  errorsCancellable = HyperTrack.subscribeToErrors { errors in
    for error in errors {
      switch error {
      case .permissions(.location(.denied)),
           .permissions(.location(.insufficientForBackground)),
           .permissions(.location(.reducedAccuracy)),
           .permissions(.location(.provisional)):
        // Explain and link to Settings.
        break
      case .permissions(.location(.notDetermined)):
        // Run the permission flow.
        break
      case .location(.servicesDisabled):
        // Ask the worker to turn on Location Services.
        break
      default:
        // .location(.mocked), .location(.signalLost), .invalidPublishableKey, .blockedFromRunning, ...
        break
      }
    }
  }
}

func blockingErrorsNow() -> Set<HyperTrack.Error> {
  HyperTrack.errors
}
```

## Clock-in / clock-out

```swift
import HyperTrack

func clockIn(orderHandle: String) {
  let result = HyperTrack.addGeotag(
    orderHandle: orderHandle,
    orderStatus: .clockIn,
    metadata: ["source": "worker_app"]
  )
  if case let .failure(error) = result {
    print("Clock-in recorded without a fresh location: \(error)")
  }
}

func clockOut(orderHandle: String) {
  _ = HyperTrack.addGeotag(orderHandle: orderHandle, orderStatus: .clockOut, metadata: [:])
}

func markBreak(orderHandle: String) {
  _ = HyperTrack.addGeotag(orderHandle: orderHandle, orderStatus: .custom("break_start"), metadata: [:])
}
```

Gate the button on presence at the order destination:

```swift
import HyperTrack

final class ClockInGate {
  private var ordersCancellable: HyperTrack.Cancellable?
  var onChange: (Bool) -> Void = { _ in }

  func start(orderHandle: String) {
    update(HyperTrack.orders[orderHandle]?.isInsideGeofence)
    ordersCancellable = HyperTrack.subscribeToOrders { [weak self] orders in
      self?.update(orders[orderHandle]?.isInsideGeofence)
    }
  }

  private func update(_ result: Result<Bool, HyperTrack.Location.Error>?) {
    switch result {
    case .success(true)?: onChange(true)
    default: onChange(false) // not inside, order not received yet, or location error
    }
  }
}
```

## Availability (Nearby)

```swift
import HyperTrack

func setAvailable(_ available: Bool) {
  HyperTrack.isAvailable = available
}
```

## On-device orders (offline-first apps only)

```swift
import HyperTrack

func startOfflineOrder() {
  let result = HyperTrack.orders.track(
    trackMode: .onShift,
    orders: [
      HyperTrack.TrackOrder(
        orderHandle: "shift-123",
        destination: .circular(
          HyperTrack.Destination.Circular(
            center: HyperTrack.Location(latitude: 37.795409, longitude: -122.393403),
            radius: 100
          )
        )
      ),
    ]
  )
  if case let .failure(error) = result {
    print("Orders not tracked: \(error)")
  }
}

func finishOfflineOrder() {
  HyperTrack.orders["shift-123"]?.complete() // or .cancel()
}
```

Track modes: `.preShift`, `.onShift`, `.fullShift`.
