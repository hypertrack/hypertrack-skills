# Android SDK Integration

## Requirements

- Android 5.0+ (API 21+)
- `targetSdk`: must meet current Google Play minimum
- CPU architectures: arm64-v8a, armeabi-v7a, x86_64, x86 (emulators supported)
- Google Play Services required on device (Huawei HMS not supported)
- Firebase Cloud Messaging SDK 23.1.1+ (added as dependency)

## Add SDK dependency

### 1. Add HyperTrack Maven repository

In your **project-level** Gradle config:

```kotlin
// settings.gradle.kts (Gradle 6.8+, required in Gradle 8+)
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

```groovy
// settings.gradle (Groovy)
dependencyResolutionManagement {
    repositories {
        google()
        mavenCentral()
        maven {
            name 'hypertrack'
            url 'https://s3-us-west-2.amazonaws.com/m2.hypertrack.com/'
        }
    }
}
```

If using older Gradle without centralized repos, add to both `app/build.gradle` and root `build.gradle`:

```groovy
allprojects {
    repositories {
        google()
        mavenCentral()
        maven {
            name 'hypertrack'
            url 'https://s3-us-west-2.amazonaws.com/m2.hypertrack.com/'
        }
    }
}
```

### 2. Add SDK dependencies

In `app/build.gradle(.kts)`:

```kotlin
dependencies {
    implementation("com.hypertrack:sdk-android:<version>")
    implementation("com.hypertrack:location-services-google:<version>")
    implementation("com.hypertrack:push-service-firebase:<version>")
}
```

```groovy
dependencies {
    implementation 'com.hypertrack:sdk-android:<version>'
    implementation 'com.hypertrack:location-services-google:<version>'
    implementation 'com.hypertrack:push-service-firebase:<version>'
}
```

> All three dependencies must use the same version.

### 3. Sync Gradle

Run **Sync Project with Gradle Files** after adding dependencies.

## Configure ProGuard

If using `minifyEnabled true`, add to `proguard-rules.pro`:

```
-keepnames class kotlinx.coroutines.internal.MainDispatcherFactory {}
-keepnames class kotlinx.coroutines.CoroutineExceptionHandler {}
-keepclassmembernames class kotlinx.** {
    volatile <fields>;
}
-keep class kotlinx.coroutines.android.AndroidDispatcherFactory {*;}
```

## Set up silent push notifications

HyperTrack requires Firebase Cloud Messaging (FCM) to:
- Start/stop tracking when orders are created/completed server-side
- Wake up the app if the OS killed it

**This is mandatory.** Without FCM, remote tracking will not work.

### 1. Set up Firebase in your app

Follow [Firebase Android setup](https://firebase.google.com/docs/android/setup) if not already done.

### 2. Get a Google Cloud Service account key

You need a JSON key for a service account with Firebase Cloud Messaging access.

**Method 1 — Firebase Console (quick, broad permissions):**
1. Go to Firebase Console → Project Settings → Service accounts
2. Verify Firebase Cloud Messaging API (V1) is enabled
3. Click "Generate new private key"
4. Download the JSON key file

**Method 2 — Fine-grained key (recommended for production):**
1. Go to Firebase Console → click "Manage service account permissions"
2. Create a new service account with **Firebase Cloud Messaging API Admin** role
3. Wait 10–15 min for Google to provision
4. Open the Keys tab → Create new JSON key → Download

### 3. Upload to HyperTrack dashboard

Go to [Setup page](https://dashboard.hypertrack.com/setup) → "Server to Device communication" section → paste the JSON key contents.

## Set the publishable key

In `AndroidManifest.xml`:

```xml
<application>
    <meta-data
        android:name="HyperTrackPublishableKey"
        android:value="your-publishable-key-here" />
</application>
```

## Set worker handle

On login or app launch:

```kotlin
HyperTrack.workerHandle = "your_user_id"
```

```java
HyperTrack.setWorkerHandle("your_user_id");
```

On logout:

```kotlin
HyperTrack.workerHandle = ""
```

## Set name and metadata (optional)

```kotlin
import com.hypertrack.sdk.android.Json

HyperTrack.name = "James Rodriguez"

val metadata = Json.fromMap(mapOf(
    "department" to "delivery",
    "vehicle_type" to "van",
    "zone" to "northeast"
))
if (metadata != null) {
    HyperTrack.metadata = metadata
}
```

```java
import com.hypertrack.sdk.android.Json;

HyperTrack.setName("James Rodriguez");

Map<String, Object> map = new HashMap<>();
map.put("department", "delivery");
map.put("vehicle_type", "van");
Json.Object metadata = Json.Companion.fromMap(map);
if (metadata != null) {
    HyperTrack.setMetadata(metadata);
}
```

## Grant permissions

Required runtime permissions:

| Permission | Required | Notes |
|-----------|----------|-------|
| `ACCESS_FINE_LOCATION` | Yes | Core location tracking |
| `ACCESS_BACKGROUND_LOCATION` | Yes (Android 11+ / API 30+) | Must request separately after fine location is granted |

### Request permissions in code

```kotlin
// Step 1: Request fine location
ActivityCompat.requestPermissions(activity,
    arrayOf(Manifest.permission.ACCESS_FINE_LOCATION), REQUEST_CODE)

// Step 2: After fine location granted, request background (Android 11+)
if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
    ActivityCompat.requestPermissions(activity,
        arrayOf(Manifest.permission.ACCESS_BACKGROUND_LOCATION), REQUEST_CODE_BG)
}
```

### Google Play background location review

Apps that request `ACCESS_BACKGROUND_LOCATION` must submit a declaration in the Google Play Console explaining why background access is needed. Plan for this during app review.

## Android battery optimization (whitelisting)

Many Android manufacturers (Samsung, Xiaomi, Vivo, OnePlus, OPPO) include aggressive battery savers that kill background apps. The user must whitelist your app.

Common outage indicators in the dashboard:
- "Tracking services terminated"
- "SDK killed by user"
- "Refresh status denied"

**Instruct workers to whitelist the app.** Device-specific guides:
- Samsung: Settings → Battery → App power management → add to "Unmonitored apps"
- Xiaomi/Redmi: Settings → Battery → App battery saver → choose "No restrictions"
- See https://dontkillmyapp.com for all manufacturers
- See [HyperTrack whitelisting guide](https://hypertrack.com/docs/whitelisting) for video instructions

## Handle errors

```kotlin
val cancellable = HyperTrack.subscribeToErrors { errors ->
    errors.forEach { error ->
        when (error) {
            is HyperTrack.Error.Permissions.Location.Denied -> {
                // Prompt user to grant location permission
            }
            is HyperTrack.Error.Location.ServicesDisabled -> {
                // Prompt user to enable Location Services
            }
            else -> {
                Log.w("HyperTrack", "Error: $error")
            }
        }
    }
}
```

Or query synchronously:

```kotlin
HyperTrack.errors.forEach { error ->
    // handle
}
```

See [Error API Reference](https://hypertrack.github.io/sdk-android/) for the full list.

## Add geotags (optional)

```kotlin
// Clock in
HyperTrack.addGeotag(
    orderHandle = "shift-123",
    orderStatus = HyperTrack.OrderStatus.ClockIn,
    metadata = Json.fromMap(mapOf("facility" to "Building A"))
)

// Clock out
HyperTrack.addGeotag(
    orderHandle = "shift-123",
    orderStatus = HyperTrack.OrderStatus.ClockOut,
    metadata = Json.fromMap(mapOf())
)
```

## Worker availability (optional)

```kotlin
HyperTrack.isAvailable = true   // Ready for assignments
HyperTrack.isAvailable = false  // Off-duty
```

## Verification checklist

- [ ] App builds with all HyperTrack dependencies resolved
- [ ] Gradle sync succeeds
- [ ] `HyperTrackPublishableKey` set in AndroidManifest.xml
- [ ] `HyperTrack.workerHandle` set on login
- [ ] Fine location + background location permissions granted
- [ ] Firebase configured and FCM service account key uploaded to dashboard
- [ ] `HyperTrack.errors` returns an empty set
- [ ] Worker appears on [HyperTrack dashboard](https://dashboard.hypertrack.com)
- [ ] App whitelisted from battery optimization on test device

## References

- [HyperTrack Android SDK Reference](https://hypertrack.github.io/sdk-android/)
- [Quickstart app](https://github.com/hypertrack/quickstart-android)
- [Install guide](https://hypertrack.com/docs/install-sdk-android)
- [FCM service account setup](https://hypertrack.com/docs/fcm-service-account)
