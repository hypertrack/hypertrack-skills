# Android SDK

Requires Android 5.0+ (API 21), Google Play Services on the device (Huawei HMS isn't supported), and Firebase Cloud Messaging 23.1.1+. `targetSdk` must meet Google Play's current minimum. Kotlin blocks here compile against the HyperTrack Android SDK. If something doesn't compile against a newer SDK, check the [SDK reference](https://hypertrack.github.io/mobile/sdk-android/latest/-hyper-track%20-s-d-k%20for%20-android/com.hypertrack.sdk.android/-hyper-track/index.html) and `CHANGELOG.md` in `hypertrack/sdk-android`.

## Install

Add HyperTrack's Maven repository. With centralized repositories (`settings.gradle(.kts)`, the default since Gradle 8):

```kts
dependencyResolutionManagement {
    repositories {
        google()
        mavenCentral()
        maven {
            name = "hypertrack"
            url = uri("https://s3-us-west-2.amazonaws.com/m2.hypertrack.com/")
        }
    }
}
```

Without centralized repositories, add the same `maven { ... }` entry under `allprojects { repositories { ... } }` in the project-level `build.gradle(.kts)`.

Dependencies (app module). **All HyperTrack artifacts use the same version:**

```kts
dependencies {
    implementation("com.hypertrack:sdk-android:<version>")
    implementation("com.hypertrack:location-services-google:<version>") // required: location plugin
    implementation("com.hypertrack:push-service-firebase:<version>") // required: push plugin
    implementation("com.hypertrack:activity-service-google:<version>") // optional: activity detection
}
```

- Latest version: `tag_name` from `https://api.github.com/repos/hypertrack/sdk-android/releases/latest`. It matches the `<latest>` in `https://s3-us-west-2.amazonaws.com/m2.hypertrack.com/com/hypertrack/sdk-android/maven-metadata-sdk-android.xml`.
- If the app (or another library) pins `com.google.android.gms:play-services-location` to 19.0.1 or older, use `location-services-google-19-0-1` instead of `location-services-google`. Otherwise you get `IncompatibleClassChangeError: Found interface com.google.android.gms.location.FusedLocationProviderClient` and no locations. Check with `./gradlew app:dependencies | grep play-services-location`.
- `activity-service-google` declares `ACTIVITY_RECOGNITION`. Request it at runtime if you include the plugin.

If R8/ProGuard minification is on, add to `proguard-rules.pro`:

```text
-keepnames class kotlinx.coroutines.internal.MainDispatcherFactory {}
-keepnames class kotlinx.coroutines.CoroutineExceptionHandler {}
-keepclassmembernames class kotlinx.** {
    volatile <fields>;
}
-keep class kotlinx.coroutines.android.AndroidDispatcherFactory {*;}
```

## Manifest

```xml
<application>
    <meta-data
        android:name="HyperTrackPublishableKey"
        android:value="YOUR_PUBLISHABLE_KEY" />
    <!-- Optional: foreground-service notification copy (string resources) -->
    <meta-data
        android:name="HyperTrackForegroundNotificationTitle"
        android:resource="@string/tracking_notification_title" />
    <meta-data
        android:name="HyperTrackForegroundNotificationText"
        android:resource="@string/tracking_notification_text" />
</application>
```

The SDK merges its own permissions (location, foreground service, boot completed, and so on) into the manifest. Tracking runs as a foreground service with a persistent notification. Its text should say that location is being tracked.

## Silent push (FCM)

1. Firebase must be set up in the app: `google-services.json` in the app module and the `com.google.gms.google-services` Gradle plugin applied. `push-service-firebase` brings in `firebase-messaging`.
2. Create a Google Cloud service-account JSON key for the same Firebase project.
   - **Quick:** Firebase Console → Project settings → Service accounts → Generate new private key.
   - **Least privilege:** a dedicated service account with the **Firebase Cloud Messaging API Admin** role. It takes 10–15 min to propagate.
   - Check that the Firebase Cloud Messaging API (V1) is enabled.
3. On the dashboard [Setup page](https://dashboard.hypertrack.com/setup), paste the JSON under "Server to Device communication".

The key's project, the app's package name, and the build variant's `google-services.json` must all match. Debug builds with a different application ID or an unregistered signature are a common cause of silent failures.

## Worker handle, name, metadata

```kotlin
import com.hypertrack.sdk.android.HyperTrack
import com.hypertrack.sdk.android.Json

fun onLogin(userId: String, displayName: String) {
    HyperTrack.workerHandle = userId
    HyperTrack.name = displayName
    Json.fromMap(mapOf("team" to "north", "vehicle" to "van"))?.let { HyperTrack.metadata = it }
}

fun onLogout() {
    HyperTrack.workerHandle = ""
}
```

`Json.fromMap` and `Json.fromString` return `null` for input that isn't valid JSON. Build `Json.Object(mapOf("k" to Json.String("v")))` directly when you need a non-null value.

## Location permissions

Request in two steps (see `mobile.md` § Permissions): `ACCESS_FINE_LOCATION` + `ACCESS_COARSE_LOCATION`, then `ACCESS_BACKGROUND_LOCATION` separately on API 29+. Show a prominent disclosure before each step. Use the Activity Result API (`ActivityResultContracts.RequestMultiplePermissions` / `RequestPermission`).

## Errors

```kotlin
import com.hypertrack.sdk.android.HyperTrack

// Retain the cancellable while the screen needs updates; call cancel() when done.
fun observeErrors(): HyperTrack.Cancellable =
    HyperTrack.subscribeToErrors { errors ->
        errors.forEach { error ->
            when (error) {
                is HyperTrack.Error.Permissions.Location.Denied,
                is HyperTrack.Error.Permissions.Location.InsufficientForBackground,
                is HyperTrack.Error.Permissions.Location.ReducedAccuracy -> {
                    // Explain and open the app's settings.
                }
                is HyperTrack.Error.Location.ServicesDisabled -> {
                    // Ask the worker to turn on location.
                }
                is HyperTrack.Error.NoExemptionFromBackgroundStartRestrictions -> {
                    // OS blocked a background start; ask the worker to open the app.
                }
                else -> {
                    // Mocked, SignalLost, ServicesUnavailable, InvalidPublishableKey, BlockedFromRunning, ...
                }
            }
        }
    }

fun blockingErrorsNow(): Set<HyperTrack.Error> = HyperTrack.errors
```

## Clock-in / clock-out

```kotlin
import com.hypertrack.sdk.android.HyperTrack
import com.hypertrack.sdk.android.Json
import com.hypertrack.sdk.android.Result

fun clockIn(orderHandle: String) {
    val metadata = Json.Object(mapOf("source" to Json.String("worker_app")))
    when (val result = HyperTrack.addGeotag(orderHandle, HyperTrack.OrderStatus.ClockIn, metadata)) {
        is Result.Success -> Unit
        is Result.Failure -> println("Clock-in recorded without a fresh location: ${result.failure}")
    }
}

fun clockOut(orderHandle: String) {
    HyperTrack.addGeotag(orderHandle, HyperTrack.OrderStatus.ClockOut, Json.Object(emptyMap()))
}

fun markBreak(orderHandle: String) {
    HyperTrack.addGeotag(orderHandle, HyperTrack.OrderStatus.Custom("break_start"), Json.Object(emptyMap()))
}
```

Gate the button on presence at the order destination:

```kotlin
import com.hypertrack.sdk.android.HyperTrack
import com.hypertrack.sdk.android.Result

fun observeClockInGate(orderHandle: String, onChange: (Boolean) -> Unit): HyperTrack.Cancellable {
    fun update(result: Result<Boolean, HyperTrack.LocationError>?) {
        // false when not inside, the order isn't received yet, or location failed
        onChange(result is Result.Success && result.success)
    }
    update(HyperTrack.orders[orderHandle]?.isInsideGeofence)
    return HyperTrack.subscribeToOrders { orders -> update(orders[orderHandle]?.isInsideGeofence) }
}
```

## Availability (Nearby)

```kotlin
import com.hypertrack.sdk.android.HyperTrack

fun setAvailable(available: Boolean) {
    HyperTrack.isAvailable = available
}
```

## On-device orders (offline-first apps only)

```kotlin
import com.hypertrack.sdk.android.HyperTrack
import com.hypertrack.sdk.android.Result

fun startOfflineOrder() {
    val result = HyperTrack.orders.track(
        HyperTrack.OrderTrackMode.OnShift,
        listOf(
            HyperTrack.TrackOrder(
                orderHandle = "shift-123",
                destination = HyperTrack.Destination.Circular(
                    center = HyperTrack.Location(latitude = 37.795409, longitude = -122.393403),
                    radius = 100,
                ),
            ),
        ),
    )
    if (result is Result.Failure) println("Orders not tracked: ${result.failure.error}")
}

fun finishOfflineOrder() {
    HyperTrack.orders["shift-123"]?.complete() // or cancel()
}
```

Track modes: `OrderTrackMode.PreShift`, `OnShift`, `FullShift`.

## Testing gotchas (Android)

- **Force stop blocks FCM until the next manual launch.** That includes Settings → Force stop, killing from Android Studio, and `adb shell am force-stop`. To test wake-up from a killed state, reboot, or swipe the app away without force-stopping.
- Check FCM delivery with the Firebase debug menu: dial `*#*#426#*#*` → Events.
- Emulator location simulation isn't flagged as mocked. Mock-location apps on real devices are (see `HyperTrackAllowMockLocation`).
